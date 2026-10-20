import hashlib
import json
import os
import tempfile
import unittest

from decentral.importers.extractor_pipeline import convert_batch, _parse_timestamp, _nullable


def sha(path):
    with open(path, "rb") as handle: return hashlib.sha256(handle.read()).hexdigest()


class PipelineTests(unittest.TestCase):
    def test_accepts_strict_iso_fraction_and_zone(self):
        self.assertIsNotNone(_parse_timestamp("2026-10-20T13:47:39.115Z"))
        self.assertIsNotNone(_parse_timestamp("2026-10-20T13:47:39+03:00"))
        with self.assertRaises(Exception): _parse_timestamp("2026-10-20 13:47:39")
    def test_accepts_only_boolean_or_observed_numeric_nullable(self):
        self.assertFalse(_nullable(0)); self.assertTrue(_nullable(1)); self.assertTrue(_nullable(True))
        with self.assertRaises(Exception): _nullable("YES")
    def test_converts_observed_batch_shape_and_reports_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            rows = {"schemas": [["demo"]], "relations": [["demo", "accounts", "table", "synthetic"]], "columns": [["demo", "accounts", "id", "uuid", False, "synthetic"]]}
            headers = {"schemas": ["schema"], "relations": ["schema", "name", "kind", "description"], "columns": ["schema", "relation", "name", "type", "nullable", "description"]}
            results = []
            for key in rows:
                payload = {"schema_version":1,"source":"synthetic","query_id":key,"query_sha256":"q-"+key,"captured_at":"2026-10-20T00:00:00Z","sheet":"data","columns":headers[key],"rows":rows[key],"record_count":len(rows[key])}
                name = key + ".json"; path = os.path.join(directory, name)
                with open(path, "w") as handle: json.dump(payload, handle)
                results.append({"id":key,"status":"ok","query_sha256":"q-"+key,"json":name,"json_sha256":sha(path)})
            definition = os.path.join(directory, "batch.json")
            with open(definition, "w") as handle: json.dump({"synthetic":True}, handle)
            manifest = {"schema_version":1,"run_id":"synthetic","source":"synthetic","started_at":"2026-10-20T00:00:00Z","ended_at":"2026-10-20T00:01:00Z","batch_sha256":sha(definition),"query_count":3,"results":results,"status":"complete"}
            with open(os.path.join(directory, "manifest.json"), "w") as handle: json.dump(manifest, handle)
            package, coverage = convert_batch(directory, definition)
            self.assertEqual("demo", package["schemas"][0]["name"])
            self.assertEqual("not_investigated", coverage["foreign_keys"])
