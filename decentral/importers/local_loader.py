"""Validated local snapshot loading; it never persists an uploaded file."""
import json
import os

from decentral.catalog.schema import CatalogValidationError, MAX_SNAPSHOT_BYTES, validate_snapshot


def load_snapshot_bytes(payload):
    if not isinstance(payload, bytes) or len(payload) > MAX_SNAPSHOT_BYTES:
        raise CatalogValidationError("snapshot exceeds the 1 MiB local import limit")
    try:
        parsed = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise CatalogValidationError("snapshot must be UTF-8 JSON")
    return validate_snapshot(parsed)


def load_snapshot_file(path):
    """Trusted local startup path; HTTP uploads remain capped at 1 MiB."""
    if os.path.getsize(path) > 50 * 1024 * 1024:
        raise CatalogValidationError("local snapshot exceeds the 50 MiB limit")
    with open(path, "rb") as handle:
        payload = handle.read()
    try:
        return validate_snapshot(json.loads(payload.decode("utf-8")))
    except (UnicodeDecodeError, ValueError):
        raise CatalogValidationError("snapshot must be UTF-8 JSON")
