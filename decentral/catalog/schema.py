"""Strict validation for portable, non-sensitive catalog snapshots."""
import hashlib
import json

FORMAT = "decentral.catalog/v1"
MAX_SNAPSHOT_BYTES = 1024 * 1024


class CatalogValidationError(ValueError):
    pass


def canonical_bytes(snapshot):
    """Stable representation used to verify the declared content hash."""
    body = dict(snapshot)
    body.pop("content_sha256", None)
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")


def content_hash(snapshot):
    return hashlib.sha256(canonical_bytes(snapshot)).hexdigest()


def _exact_keys(value, keys, path):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise CatalogValidationError("%s must contain exactly: %s" % (path, ", ".join(keys)))


def _text(value, path, max_length=200):
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        raise CatalogValidationError("%s must be non-empty text up to %d characters" % (path, max_length))


def _provenance(value, path):
    _exact_keys(value, ("status", "source", "evidence"), path)
    if value["status"] not in ("declarada", "corroborada", "hipotesis"):
        raise CatalogValidationError("%s.status is invalid" % path)
    _text(value["source"], path + ".source")
    _text(value["evidence"], path + ".evidence", 500)


def validate_snapshot(snapshot):
    _exact_keys(snapshot, (
        "format", "snapshot_id", "generated_at", "source", "content_sha256",
        "entities", "relationships"
    ), "snapshot")
    if snapshot["format"] != FORMAT:
        raise CatalogValidationError("unsupported catalog format")
    for field in ("snapshot_id", "generated_at", "source"):
        _text(snapshot[field], "snapshot." + field)
    if not isinstance(snapshot["content_sha256"], str) or len(snapshot["content_sha256"]) != 64:
        raise CatalogValidationError("snapshot.content_sha256 must be a SHA-256 hex value")
    if snapshot["content_sha256"] != content_hash(snapshot):
        raise CatalogValidationError("snapshot.content_sha256 does not match its content")
    if not isinstance(snapshot["entities"], list) or not snapshot["entities"]:
        raise CatalogValidationError("snapshot.entities must be a non-empty list")
    names = set()
    entity_columns = {}
    for index, entity in enumerate(snapshot["entities"]):
        path = "entities[%d]" % index
        _exact_keys(entity, ("name", "label", "description", "provenance", "columns", "indexes"), path)
        _text(entity["name"], path + ".name")
        if entity["name"] in names:
            raise CatalogValidationError("entity names must be unique")
        names.add(entity["name"])
        _text(entity["label"], path + ".label")
        _text(entity["description"], path + ".description", 500)
        _provenance(entity["provenance"], path + ".provenance")
        if not isinstance(entity["columns"], list) or not entity["columns"]:
            raise CatalogValidationError(path + ".columns must be a non-empty list")
        column_names = set()
        for column in entity["columns"]:
            _exact_keys(column, ("name", "type", "nullable", "key", "description", "provenance"), path + ".column")
            _text(column["name"], path + ".column.name")
            if column["name"] in column_names:
                raise CatalogValidationError("column names must be unique per entity")
            column_names.add(column["name"])
            _text(column["type"], path + ".column.type")
            if not isinstance(column["nullable"], bool) or column["key"] not in ("primary", "foreign", "none"):
                raise CatalogValidationError("invalid column attributes")
            _text(column["description"], path + ".column.description", 500)
            _provenance(column["provenance"], path + ".column.provenance")
        entity_columns[entity["name"]] = column_names
        if not isinstance(entity["indexes"], list):
            raise CatalogValidationError(path + ".indexes must be a list")
        for item in entity["indexes"]:
            _exact_keys(item, ("name", "columns", "unique", "provenance"), path + ".index")
            _text(item["name"], path + ".index.name")
            if not isinstance(item["columns"], list) or not item["columns"] or not all(c in column_names for c in item["columns"]):
                raise CatalogValidationError("index columns must refer to known columns")
            if not isinstance(item["unique"], bool):
                raise CatalogValidationError("index.unique must be boolean")
            _provenance(item["provenance"], path + ".index.provenance")
    if not isinstance(snapshot["relationships"], list):
        raise CatalogValidationError("snapshot.relationships must be a list")
    for index, relation in enumerate(snapshot["relationships"]):
        path = "relationships[%d]" % index
        _exact_keys(relation, ("from_entity", "from_column", "to_entity", "to_column", "cardinality", "provenance"), path)
        if relation["from_entity"] not in names or relation["to_entity"] not in names:
            raise CatalogValidationError("relationship entity is unknown")
        if relation["from_column"] not in entity_columns[relation["from_entity"]] or relation["to_column"] not in entity_columns[relation["to_entity"]]:
            raise CatalogValidationError("relationship column is unknown")
        if relation["cardinality"] not in ("one-to-one", "one-to-many", "many-to-many"):
            raise CatalogValidationError("relationship cardinality is invalid")
        _provenance(relation["provenance"], path + ".provenance")
    return snapshot
