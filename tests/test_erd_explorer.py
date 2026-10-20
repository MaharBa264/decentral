import json
import os
import unittest

from decentral.catalog.repository import CatalogRepository
from decentral.importers.metadata_package import PostgresMetadataPackageAdapter, package_hash


ROOT = os.path.dirname(os.path.dirname(__file__))


def synthetic_package():
    p = {
        "format": "decentral.metadata-package/v1",
        "package_id": "synthetic-erd-pkg",
        "generated_at": "2026-10-20T00:00:00Z",
        "source": "synthetic test package",
        "content_sha256": "",
        "schemas": [
            {"name": "sales", "provenance": {"status": "declarada", "source": "test", "evidence": "fixture"}},
            {"name": "analytics", "provenance": {"status": "declarada", "source": "test", "evidence": "fixture"}}
        ],
        "relations": [
            {
                "schema": "sales",
                "name": "customers",
                "kind": "table",
                "description": "Tabla de clientes comerciales",
                "provenance": {"status": "declarada", "source": "test", "evidence": "fixture"},
                "columns": [
                    {"name": "tenant_id", "type": "uuid", "nullable": False, "description": "Partición multitenant", "provenance": {"status": "declarada", "source": "test", "evidence": "fixture"}},
                    {"name": "customer_id", "type": "uuid", "nullable": False, "description": "Identificador de cliente", "provenance": {"status": "declarada", "source": "test", "evidence": "fixture"}},
                    {"name": "company_name", "type": "varchar(200)", "nullable": False, "description": "Razón social del cliente", "provenance": {"status": "declarada", "source": "test", "evidence": "fixture"}}
                ],
                "primary_key": {
                    "name": "pk_customers",
                    "columns": ["tenant_id", "customer_id"],
                    "provenance": {"status": "corroborada", "source": "test", "evidence": "fixture"}
                },
                "foreign_keys": [],
                "indexes": [
                    {"name": "pk_customers", "columns": ["tenant_id", "customer_id"], "unique": True, "provenance": {"status": "corroborada", "source": "test", "evidence": "fixture"}},
                    {"name": "ix_customers_name", "columns": ["company_name"], "unique": False, "provenance": {"status": "declarada", "source": "test", "evidence": "fixture"}}
                ]
            },
            {
                "schema": "sales",
                "name": "orders",
                "kind": "table",
                "description": "Órdenes de compra registradas",
                "provenance": {"status": "corroborada", "source": "test", "evidence": "fixture"},
                "columns": [
                    {"name": "tenant_id", "type": "uuid", "nullable": False, "description": "Partición multitenant", "provenance": {"status": "declarada", "source": "test", "evidence": "fixture"}},
                    {"name": "order_id", "type": "uuid", "nullable": False, "description": "Identificador de la orden", "provenance": {"status": "declarada", "source": "test", "evidence": "fixture"}},
                    {"name": "customer_id", "type": "uuid", "nullable": False, "description": "Referencia al cliente de la orden", "provenance": {"status": "declarada", "source": "test", "evidence": "fixture"}},
                    {"name": "total_amount", "type": "numeric(12,2)", "nullable": False, "description": "Monto total facturado", "provenance": {"status": "declarada", "source": "test", "evidence": "fixture"}}
                ],
                "primary_key": {
                    "name": "pk_orders",
                    "columns": ["tenant_id", "order_id"],
                    "provenance": {"status": "corroborada", "source": "test", "evidence": "fixture"}
                },
                "foreign_keys": [
                    {
                        "name": "fk_orders_customer_composite",
                        "columns": ["tenant_id", "customer_id"],
                        "ref_schema": "sales",
                        "ref_relation": "customers",
                        "ref_columns": ["tenant_id", "customer_id"],
                        "provenance": {"status": "corroborada", "source": "test", "evidence": "fixture"}
                    }
                ],
                "indexes": [
                    {"name": "pk_orders", "columns": ["tenant_id", "order_id"], "unique": True, "provenance": {"status": "corroborada", "source": "test", "evidence": "fixture"}}
                ]
            },
            {
                "schema": "analytics",
                "name": "order_summary_view",
                "kind": "view",
                "description": "Vista agregada de órdenes para métricas",
                "provenance": {"status": "declarada", "source": "test", "evidence": "fixture"},
                "columns": [
                    {"name": "tenant_id", "type": "uuid", "nullable": False, "description": "Partición", "provenance": {"status": "declarada", "source": "test", "evidence": "fixture"}},
                    {"name": "order_count", "type": "bigint", "nullable": False, "description": "Total de órdenes", "provenance": {"status": "declarada", "source": "test", "evidence": "fixture"}}
                ],
                "primary_key": None,
                "foreign_keys": [],
                "indexes": []
            }
        ]
    }
    p["content_sha256"] = package_hash(p)
    return p


class ErdExplorerTests(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(ROOT, "catalog", "synthetic-demo.json"), "r") as handle:
            self.demo_snapshot = json.load(handle)

    def test_erd_graph_from_h0_snapshot(self):
        repo = CatalogRepository(self.demo_snapshot)
        graph = repo.erd_graph()
        self.assertEqual(["public"], graph["schemas"])
        self.assertEqual(3, len(graph["nodes"]))
        self.assertEqual(2, len(graph["edges"]))
        self.assertEqual(3, graph["coverage"]["counts"]["relations"])
        self.assertEqual(0, graph["coverage"]["counts"]["composite_foreign_keys"])

    def test_erd_graph_preserves_composite_fk_as_single_constraint_and_unknown_cardinality(self):
        pkg = synthetic_package()
        coverage = {
            "foreign_keys_external_targets": {
                "state": "partial",
                "rows": 5,
                "resolution": "batch"
            }
        }
        adapter = PostgresMetadataPackageAdapter()
        snapshot = adapter.to_snapshot(pkg)
        repo = CatalogRepository(snapshot, package=pkg, coverage=coverage)

        graph = repo.erd_graph()
        self.assertEqual(["analytics", "sales"], graph["schemas"])
        self.assertEqual(3, len(graph["nodes"]))
        self.assertEqual(1, len(graph["edges"]))

        edge = graph["edges"][0]
        self.assertEqual("sales.orders->sales.customers:fk_orders_customer_composite", edge["id"])
        self.assertTrue(edge["is_composite"])
        self.assertEqual(["tenant_id", "customer_id"], edge["columns"])
        self.assertEqual(["tenant_id", "customer_id"], edge["ref_columns"])
        self.assertEqual("unknown", edge["cardinality"])
        self.assertEqual("partial", edge["coverage"])

    def test_erd_search_by_schema_table_view_column_and_description(self):
        pkg = synthetic_package()
        adapter = PostgresMetadataPackageAdapter()
        snapshot = adapter.to_snapshot(pkg)
        repo = CatalogRepository(snapshot, package=pkg)

        # 1. Search by schema
        by_schema = repo.erd_graph(schema="analytics")
        matches = [n["name"] for n in by_schema["nodes"] if n["matches"]]
        self.assertEqual(["order_summary_view"], matches)

        # 2. Search by table name
        by_table = repo.erd_graph(query="customers")
        matches = [n["name"] for n in by_table["nodes"] if n["matches"]]
        self.assertEqual(["customers"], matches)

        # 3. Search by view kind
        by_view = repo.erd_graph(query="view")
        matches = [n["name"] for n in by_view["nodes"] if n["matches"]]
        self.assertEqual(["order_summary_view"], matches)

        # 4. Search by column name
        by_col = repo.erd_graph(query="total_amount")
        matches = [n["name"] for n in by_col["nodes"] if n["matches"]]
        self.assertEqual(["orders"], matches)

        # 5. Search by description
        by_desc = repo.erd_graph(query="métricas")
        matches = [n["name"] for n in by_desc["nodes"] if n["matches"]]
        self.assertEqual(["order_summary_view"], matches)

    def test_erd_does_not_invent_unrelated_edges(self):
        pkg = synthetic_package()
        adapter = PostgresMetadataPackageAdapter()
        snapshot = adapter.to_snapshot(pkg)
        repo = CatalogRepository(snapshot, package=pkg)

        graph = repo.erd_graph()
        edge_pairs = [(e["from_entity"], e["to_entity"]) for e in graph["edges"]]
        self.assertEqual([("sales.orders", "sales.customers")], edge_pairs)
        self.assertNotIn(("analytics.order_summary_view", "sales.orders"), edge_pairs)
        self.assertNotIn(("analytics.order_summary_view", "sales.customers"), edge_pairs)
