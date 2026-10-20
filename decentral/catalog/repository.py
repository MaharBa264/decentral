"""Read-only catalog queries used by the HTTP API and future clients."""
from decentral.catalog.schema import validate_snapshot


class CatalogRepository(object):
    def __init__(self, snapshot, package=None, coverage=None):
        self.snapshot = validate_snapshot(snapshot)
        self.package = package
        self.coverage = coverage or {}
        self._entities = {item["name"]: item for item in snapshot["entities"]}

    def metadata(self):
        meta = {key: self.snapshot[key] for key in ("format", "snapshot_id", "generated_at", "source", "content_sha256")}
        if self.package:
            meta["package_id"] = self.package.get("package_id")
            meta["package_format"] = self.package.get("format")
        if self.coverage:
            meta["coverage"] = self.coverage
        return meta

    def list_entities(self, query=""):
        needle = query.lower().strip()
        entities = self.snapshot["entities"]
        if needle:
            entities = [
                item for item in entities
                if needle in (
                    item["name"] + " " + item["label"] + " " + item["description"] + " " +
                    " ".join(c.get("name", "") + " " + c.get("description", "") for c in item.get("columns", []))
                ).lower()
            ]
        return [{key: item[key] for key in ("name", "label", "description", "provenance")} for item in entities]

    def entity(self, name):
        return self._entities.get(name)

    def relationships(self, entity=None):
        relationships = self.snapshot["relationships"]
        if entity:
            relationships = [item for item in relationships if entity in (item["from_entity"], item["to_entity"])]
        return relationships

    def erd_graph(self, schema=None, query=""):
        nodes = []
        schemas = set()
        needle = query.lower().strip()

        for e in self.snapshot["entities"]:
            parts = e["name"].split(".", 1)
            e_schema = parts[0] if len(parts) > 1 else "public"
            name = parts[1] if len(parts) > 1 else e["name"]
            kind = "view" if (e.get("description", "").startswith("view:") or "vista" in e.get("description", "").lower()) else "table"
            schemas.add(e_schema)

            columns = e.get("columns", [])
            indexes = e.get("indexes", [])

            # Search match condition across schema, table, view, column names, and descriptions
            searchable_text = (
                e_schema + " " + name + " " + kind + " " + e.get("label", "") + " " + e.get("description", "") + " " +
                " ".join(c.get("name", "") + " " + c.get("description", "") for c in columns)
            ).lower()

            matches = True
            if schema and e_schema != schema:
                matches = False
            if needle and needle not in searchable_text:
                matches = False

            nodes.append({
                "id": e["name"],
                "name": name,
                "schema": e_schema,
                "kind": kind,
                "label": e.get("label", e["name"]),
                "description": e.get("description", ""),
                "provenance": e.get("provenance", {}),
                "columns": columns,
                "indexes": indexes,
                "matches": matches,
            })

        edges = []
        ext_target_cov = self.coverage.get("foreign_keys_external_targets")
        is_partial_cov = isinstance(ext_target_cov, dict) and ext_target_cov.get("state") == "partial"

        if self.package and "relations" in self.package:
            for r in self.package.get("relations", []):
                source_id = r["schema"] + "." + r["name"]
                for fk in r.get("foreign_keys", []):
                    target_id = fk["ref_schema"] + "." + fk["ref_relation"]
                    edges.append({
                        "id": source_id + "->" + target_id + ":" + fk["name"],
                        "name": fk["name"],
                        "from_entity": source_id,
                        "to_entity": target_id,
                        "columns": fk["columns"],
                        "ref_columns": fk["ref_columns"],
                        "is_composite": len(fk["columns"]) > 1,
                        "cardinality": "unknown",
                        "coverage": "partial" if is_partial_cov else "confirmed",
                        "provenance": fk.get("provenance", {})
                    })
        else:
            for rel in self.snapshot.get("relationships", []):
                edges.append({
                    "id": rel["from_entity"] + "->" + rel["to_entity"] + ":" + rel["from_column"],
                    "name": rel.get("from_column") + "->" + rel.get("to_column"),
                    "from_entity": rel["from_entity"],
                    "to_entity": rel["to_entity"],
                    "columns": [rel["from_column"]],
                    "ref_columns": [rel["to_column"]],
                    "is_composite": False,
                    "cardinality": rel.get("cardinality", "unknown"),
                    "coverage": "confirmed",
                    "provenance": rel.get("provenance", {})
                })

        return {
            "schemas": sorted(list(schemas)),
            "nodes": nodes,
            "edges": edges,
            "coverage": {
                "external_targets": ext_target_cov if is_partial_cov else None,
                "counts": {
                    "schemas": len(schemas),
                    "relations": len(nodes),
                    "relationships": len(edges),
                    "composite_foreign_keys": sum(1 for ed in edges if ed.get("is_composite"))
                }
            }
        }

