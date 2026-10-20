import copy
import json
import os
import unittest

from decentral.catalog.repository import CatalogRepository
from decentral.catalog.schema import CatalogValidationError, content_hash, validate_snapshot
from decentral.importers.local_loader import load_snapshot_bytes


ROOT = os.path.dirname(os.path.dirname(__file__))


def fixture():
    with open(os.path.join(ROOT, "catalog", "synthetic-demo.json"), "r") as handle:
        return json.load(handle)


class CatalogTests(unittest.TestCase):
    def test_synthetic_snapshot_is_valid_and_versioned(self):
        snapshot = validate_snapshot(fixture())
        self.assertEqual("decentral.catalog/v1", snapshot["format"])
        self.assertEqual(snapshot["content_sha256"], content_hash(snapshot))

    def test_search_and_entity_detail(self):
        repository = CatalogRepository(fixture())
        self.assertEqual(["demo_projects"], [x["name"] for x in repository.list_entities("proyectos")])
        self.assertEqual("uuid", repository.entity("demo_projects")["columns"][0]["type"])

    def test_relationships_include_only_requested_neighbourhood(self):
        repository = CatalogRepository(fixture())
        relations = repository.relationships("demo_projects")
        self.assertEqual(2, len(relations))
        self.assertTrue(all("demo_projects" in (r["from_entity"], r["to_entity"]) for r in relations))

    def test_local_import_rejects_tampered_hash_and_large_payload(self):
        changed = copy.deepcopy(fixture())
        changed["source"] = "altered"
        with self.assertRaises(CatalogValidationError):
            load_snapshot_bytes(json.dumps(changed).encode("utf-8"))
        with self.assertRaises(CatalogValidationError):
            load_snapshot_bytes(b"x" * (1024 * 1024 + 1))

    def test_relationship_columns_must_exist(self):
        changed = copy.deepcopy(fixture())
        changed["relationships"][0]["from_column"] = "missing"
        changed["content_sha256"] = content_hash(changed)
        with self.assertRaises(CatalogValidationError):
            validate_snapshot(changed)
