import unittest
from decentral.catalog.schema import CatalogValidationError
from decentral.importers.constraint_mapping import apply_constraints

P={"status":"corroborada","source":"test","evidence":"synthetic"}
class ConstraintMappingTests(unittest.TestCase):
 def test_composite_cross_schema_and_multicolumn_index(self):
  rs=[{"schema":"a","name":"x","primary_key":None,"foreign_keys":[],"indexes":[]},{"schema":"b","name":"y","primary_key":None,"foreign_keys":[],"indexes":[]}]
  apply_constraints(rs,[{"schema":"a","relation":"x","name":"pk","column_name":"one","position":1},{"schema":"a","relation":"x","name":"pk","column_name":"two","position":2}],[{"schema":"a","relation":"x","name":"fk","column_name":"one","ref_schema":"b","ref_relation":"y","ref_column":"id1","position":1},{"schema":"a","relation":"x","name":"fk","column_name":"two","ref_schema":"b","ref_relation":"y","ref_column":"id2","position":2}],[{"schema":"a","relation":"x","name":"ix","column_name":"one","position":1,"unique":False},{"schema":"a","relation":"x","name":"ix","column_name":"two","position":2,"unique":False}],P)
  self.assertEqual(["one","two"],rs[0]["primary_key"]["columns"])
 def test_accepts_zero_based_pg_index_positions(self):
  rs=[{"schema":"a","name":"x","primary_key":None,"foreign_keys":[],"indexes":[]}]
  apply_constraints(rs,[],[],[{"schema":"a","relation":"x","name":"ix","column_name":"a","position":0,"unique":True},{"schema":"a","relation":"x","name":"ix","column_name":"b","position":1,"unique":True}],P)
  self.assertEqual(["a","b"],rs[0]["indexes"][0]["columns"])
 def test_rejects_incomplete_and_nonboolean(self):
  rs=[{"schema":"a","name":"x","primary_key":None,"foreign_keys":[],"indexes":[]}]
  with self.assertRaises(CatalogValidationError): apply_constraints(rs,[],[],[{"schema":"a","relation":"x","name":"ix","column_name":"n","position":1,"unique":1}],P)
 def test_rejects_duplicate_primary_key(self):
  rs=[{"schema":"a","name":"x","primary_key":None,"foreign_keys":[],"indexes":[]}]
  rows=[{"schema":"a","relation":"x","name":"pk1","column_name":"id","position":1},{"schema":"a","relation":"x","name":"pk2","column_name":"id","position":1}]
  with self.assertRaises(CatalogValidationError): apply_constraints(rs,rows,[],[],P)
