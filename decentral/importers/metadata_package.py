"""Strict, local-only interchange for database metadata packages."""
import hashlib
import json

from decentral.catalog.schema import CatalogValidationError, content_hash, validate_snapshot
from decentral.importers.contract import CatalogExtractor

FORMAT = "decentral.metadata-package/v1"
MAX_PACKAGE_BYTES = 5 * 1024 * 1024


def _canonical(package):
    body = dict(package)
    body.pop("content_sha256", None)
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")


def package_hash(package):
    return hashlib.sha256(_canonical(package)).hexdigest()


def _keys(value, expected, path):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise CatalogValidationError("%s has unexpected fields" % path)


def _text(value, path):
    if not isinstance(value, str) or not value.strip() or len(value) > 300:
        raise CatalogValidationError("%s must be bounded non-empty text" % path)


def _provenance(value, path):
    _keys(value, ("status", "source", "evidence"), path)
    if value["status"] not in ("declarada", "corroborada", "hipotesis"):
        raise CatalogValidationError("%s has invalid status" % path)
    _text(value["source"], path + ".source")
    _text(value["evidence"], path + ".evidence")


def validate_metadata_package(package):
    _keys(package, ("format", "package_id", "generated_at", "source", "content_sha256", "schemas", "relations"), "package")
    if package["format"] != FORMAT or package["content_sha256"] != package_hash(package):
        raise CatalogValidationError("invalid metadata package format or hash")
    for field in ("package_id", "generated_at", "source"):
        _text(package[field], "package." + field)
    if not isinstance(package["schemas"], list) or not isinstance(package["relations"], list):
        raise CatalogValidationError("schemas and relations must be lists")
    schemas = set()
    for schema in package["schemas"]:
        _keys(schema, ("name", "provenance"), "schema")
        _text(schema["name"], "schema.name"); _provenance(schema["provenance"], "schema.provenance")
        if schema["name"] in schemas: raise CatalogValidationError("duplicate schema")
        schemas.add(schema["name"])
    known = set()
    for relation in package["relations"]:
        _keys(relation, ("schema", "name", "kind", "description", "provenance", "columns", "primary_key", "foreign_keys", "indexes"), "relation")
        if relation["schema"] not in schemas or relation["kind"] not in ("table", "view"):
            raise CatalogValidationError("unknown schema or relation kind")
        for field in ("name", "description"): _text(relation[field], "relation." + field)
        _provenance(relation["provenance"], "relation.provenance")
        identity = (relation["schema"], relation["name"])
        if identity in known: raise CatalogValidationError("duplicate relation")
        known.add(identity)
        columns = set()
        for column in relation["columns"]:
            _keys(column, ("name", "type", "nullable", "description", "provenance"), "column")
            for field in ("name", "type", "description"): _text(column[field], "column." + field)
            if not isinstance(column["nullable"], bool) or column["name"] in columns: raise CatalogValidationError("invalid column")
            columns.add(column["name"]); _provenance(column["provenance"], "column.provenance")
        if not columns: raise CatalogValidationError("relation requires columns")
        if relation["primary_key"] is not None:
            _keys(relation["primary_key"], ("name", "columns", "provenance"), "primary_key")
            if not relation["primary_key"]["columns"] or not set(relation["primary_key"]["columns"]).issubset(columns): raise CatalogValidationError("invalid primary key")
            _provenance(relation["primary_key"]["provenance"], "primary_key.provenance")
        for index in relation["indexes"]:
            _keys(index, ("name", "columns", "unique", "provenance"), "index")
            if not index["columns"] or not set(index["columns"]).issubset(columns) or not isinstance(index["unique"], bool): raise CatalogValidationError("invalid index")
            _provenance(index["provenance"], "index.provenance")
        for fk in relation["foreign_keys"]:
            _keys(fk, ("name", "columns", "ref_schema", "ref_relation", "ref_columns", "provenance"), "foreign_key")
            if not fk["columns"] or len(fk["columns"]) != len(fk["ref_columns"]) or not set(fk["columns"]).issubset(columns): raise CatalogValidationError("invalid foreign key")
            _provenance(fk["provenance"], "foreign_key.provenance")
    for relation in package["relations"]:
        for fk in relation["foreign_keys"]:
            target = (fk["ref_schema"], fk["ref_relation"])
            if target not in known: raise CatalogValidationError("foreign key target is unknown")
    return package


def load_metadata_package_bytes(payload):
    if not isinstance(payload, bytes) or len(payload) > MAX_PACKAGE_BYTES: raise CatalogValidationError("metadata package exceeds 5 MiB")
    try: return validate_metadata_package(json.loads(payload.decode("utf-8")))
    except (UnicodeDecodeError, ValueError): raise CatalogValidationError("metadata package must be UTF-8 JSON")


class PostgresMetadataPackageAdapter(CatalogExtractor):
    """Maps a validated metadata package to the existing read-only catalog v1."""
    def to_snapshot(self, capture):
        package = validate_metadata_package(capture)
        entities, relationships = [], []
        for relation in package["relations"]:
            primary = set((relation["primary_key"] or {}).get("columns", []))
            foreign = set(c for fk in relation["foreign_keys"] for c in fk["columns"])
            name = relation["schema"] + "." + relation["name"]
            indexes = list(relation["indexes"])
            if relation["primary_key"]: indexes.append({"name": relation["primary_key"]["name"], "columns": relation["primary_key"]["columns"], "unique": True, "provenance": relation["primary_key"]["provenance"]})
            entities.append({"name": name, "label": name, "description": relation["kind"] + ": " + relation["description"], "provenance": relation["provenance"], "columns": [{"name": c["name"], "type": c["type"], "nullable": c["nullable"], "key": "primary" if c["name"] in primary else ("foreign" if c["name"] in foreign else "none"), "description": c["description"], "provenance": c["provenance"]} for c in relation["columns"]], "indexes": indexes})
            for fk in relation["foreign_keys"]:
                for source, target in zip(fk["columns"], fk["ref_columns"]): relationships.append({"from_entity": name, "from_column": source, "to_entity": fk["ref_schema"] + "." + fk["ref_relation"], "to_column": target, "cardinality": "one-to-many", "provenance": fk["provenance"]})
        snapshot = {"format": "decentral.catalog/v1", "snapshot_id": package["package_id"], "generated_at": package["generated_at"], "source": package["source"], "content_sha256": "", "entities": entities, "relationships": relationships}
        snapshot["content_sha256"] = content_hash(snapshot)
        return validate_snapshot(snapshot)
