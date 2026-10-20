import copy
import unittest

from decentral.catalog.schema import CatalogValidationError
from decentral.importers.metadata_package import PostgresMetadataPackageAdapter, package_hash, validate_metadata_package


def package():
    p={"format":"decentral.metadata-package/v1","package_id":"synthetic-postgres-metadata","generated_at":"2026-10-20T00:00:00Z","source":"synthetic PostgreSQL metadata fixture","content_sha256":"","schemas":[{"name":"demo","provenance":{"status":"corroborada","source":"synthetic fixture","evidence":"test input"}}],"relations":[{"schema":"demo","name":"accounts","kind":"table","description":"synthetic accounts","provenance":{"status":"declarada","source":"synthetic fixture","evidence":"test input"},"columns":[{"name":"id","type":"uuid","nullable":False,"description":"synthetic id","provenance":{"status":"declarada","source":"synthetic fixture","evidence":"test input"}}],"primary_key":{"name":"accounts_pkey","columns":["id"],"provenance":{"status":"corroborada","source":"synthetic fixture","evidence":"test input"}},"foreign_keys":[],"indexes":[]},{"schema":"demo","name":"account_events","kind":"view","description":"synthetic view","provenance":{"status":"hipotesis","source":"synthetic fixture","evidence":"test input"},"columns":[{"name":"account_id","type":"uuid","nullable":False,"description":"synthetic reference","provenance":{"status":"corroborada","source":"synthetic fixture","evidence":"test input"}}],"primary_key":None,"foreign_keys":[{"name":"events_account_fk","columns":["account_id"],"ref_schema":"demo","ref_relation":"accounts","ref_columns":["id"],"provenance":{"status":"corroborada","source":"synthetic fixture","evidence":"test input"}}],"indexes":[]}]}
    p["content_sha256"]=package_hash(p)
    return p


class MetadataPackageTests(unittest.TestCase):
    def test_validates_and_adapts(self):
        snapshot=PostgresMetadataPackageAdapter().to_snapshot(package())
        self.assertEqual(["demo.accounts","demo.account_events"],[x["name"] for x in snapshot["entities"]])
        self.assertEqual("primary",snapshot["entities"][0]["columns"][0]["key"])
        self.assertEqual("foreign",snapshot["entities"][1]["columns"][0]["key"])
        self.assertEqual("demo.accounts",snapshot["relationships"][0]["to_entity"])

    def test_rejects_tampering_and_unknown_target(self):
        changed=copy.deepcopy(package()); changed["source"]="tampered"
        with self.assertRaises(CatalogValidationError): validate_metadata_package(changed)
        changed=package(); changed["relations"][1]["foreign_keys"][0]["ref_relation"]="missing"; changed["content_sha256"]=package_hash(changed)
        with self.assertRaises(CatalogValidationError): validate_metadata_package(changed)
