"""Offline conversion of an already-authorized extractor batch; never queries a source."""
import hashlib
import json
import os
from datetime import datetime

from decentral.catalog.schema import CatalogValidationError
from decentral.importers.metadata_package import package_hash, validate_metadata_package
from decentral.importers.constraint_mapping import apply_constraints

REQUIRED = ("schemas", "relations", "columns")
OPTIONAL = ("primary_keys", "foreign_keys", "indexes")


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""): h.update(chunk)
    return h.hexdigest()


def _provenance(state, query):
    return {"status": "corroborada" if state == "confirmed" else "hipotesis", "source": "authorized metadata batch", "evidence": "query %s: %s" % (query, state)}


def _records(payload):
    return [dict(zip(payload["columns"], row)) for row in payload["rows"]]


def convert_batch(batch_dir, batch_definition):
    root = os.path.realpath(batch_dir)
    if os.path.islink(os.path.join(batch_dir, "manifest.json")):
        raise CatalogValidationError("manifest symlinks are not accepted")
    try:
        with open(os.path.join(batch_dir, "manifest.json")) as handle: manifest = json.load(handle)
    except (IOError, ValueError): raise CatalogValidationError("missing or invalid batch manifest")
    required = {"schema_version","run_id","source","started_at","ended_at","batch_sha256","query_count","results","status"}
    if set(manifest) != required or manifest["schema_version"] != 1 or manifest["status"] != "complete" or manifest["query_count"] != len(manifest["results"]): raise CatalogValidationError("invalid or incomplete manifest")
    if os.path.islink(batch_definition) or _sha(batch_definition) != manifest["batch_sha256"]: raise CatalogValidationError("batch definition hash mismatch")
    try:
        for value in (manifest["started_at"], manifest["ended_at"]):
            datetime.strptime(value.replace("Z", "+0000").replace("+00:00", "+0000"), "%Y-%m-%dT%H:%M:%S%z")
    except ValueError: raise CatalogValidationError("invalid manifest timestamps")
    payloads = {}
    for entry in manifest["results"]:
        if entry.get("status") != "ok": raise CatalogValidationError("batch has a failed query")
        name = entry.get("json")
        if not isinstance(name, str) or os.path.basename(name) != name: raise CatalogValidationError("unsafe payload path")
        path=os.path.join(batch_dir,name)
        if os.path.islink(path) or os.path.commonpath((root, os.path.realpath(path))) != root or not os.path.isfile(path) or _sha(path) != entry.get("json_sha256"): raise CatalogValidationError("payload hash mismatch")
        with open(path) as handle: data=json.load(handle)
        if data.get("query_id") != entry.get("id") or data.get("query_sha256") != entry.get("query_sha256") or data.get("record_count") != len(data.get("rows",[])) or not isinstance(data.get("columns"),list): raise CatalogValidationError("payload provenance or truncation check failed")
        payloads[entry["id"]]=data
    # A large inventory arrives as deterministic pages (for example columns_p001).
    # All pages must have identical headers; their rows are concatenated only after
    # each individual manifest/hash/count check above has succeeded.
    for query in REQUIRED + OPTIONAL:
        pages=[payloads[key] for key in sorted(payloads) if key == query or key.startswith(query + "_p")]
        if pages:
            headers=pages[0]["columns"]
            if any(page["columns"] != headers for page in pages): raise CatalogValidationError("paged payload headers differ")
            payloads[query]=dict(pages[0], rows=sum((page["rows"] for page in pages), []), record_count=sum(page["record_count"] for page in pages))
    missing=[q for q in REQUIRED if q not in payloads]
    if missing: raise CatalogValidationError("required metadata queries absent: "+", ".join(missing))
    coverage={q:("confirmed" if q in payloads and payloads[q]["rows"] else ("absent_checked" if q in payloads else "not_investigated")) for q in REQUIRED+OPTIONAL}
    schemas=[{"name":r["schema"],"provenance":_provenance("confirmed","schemas")} for r in _records(payloads["schemas"])]
    relations=[]
    for r in _records(payloads["relations"]):
        if r.get("kind") not in ("table","view"): raise CatalogValidationError("relation kind must be table or view")
        relations.append({"schema":r["schema"],"name":r["name"],"kind":r["kind"],"description":r.get("description") or "metadata relation","provenance":_provenance("confirmed","relations"),"columns":[],"primary_key":None,"foreign_keys":[],"indexes":[]})
    lookup={(r["schema"],r["name"]):r for r in relations}
    for c in _records(payloads["columns"]):
        target=lookup.get((c.get("schema"),c.get("relation")))
        if not target: raise CatalogValidationError("column references unknown relation")
        if type(c["nullable"]) is not bool: raise CatalogValidationError("nullable must be boolean")
        target["columns"].append({"name":c["name"],"type":c["type"],"nullable":c["nullable"],"description":c.get("description") or "metadata column","provenance":_provenance("confirmed","columns")})
    if any(not r["columns"] for r in relations): raise CatalogValidationError("relation has no confirmed columns")
    apply_constraints(relations, _records(payloads.get("primary_keys", {"columns":[],"rows":[]})), _records(payloads.get("foreign_keys", {"columns":[],"rows":[]})), _records(payloads.get("indexes", {"columns":[],"rows":[]})), _provenance("confirmed", "constraints"))
    package={"format":"decentral.metadata-package/v1","package_id":"batch-"+manifest["run_id"],"generated_at":manifest["ended_at"],"source":"authorized PostgreSQL metadata batch","content_sha256":"","schemas":schemas,"relations":relations}
    package["content_sha256"]=package_hash(package)
    return validate_metadata_package(package),coverage
