"""Read-only catalog queries used by the HTTP API and future clients."""
from decentral.catalog.schema import validate_snapshot


class CatalogRepository(object):
    def __init__(self, snapshot):
        self.snapshot = validate_snapshot(snapshot)
        self._entities = {item["name"]: item for item in snapshot["entities"]}

    def metadata(self):
        return {key: self.snapshot[key] for key in ("format", "snapshot_id", "generated_at", "source", "content_sha256")}

    def list_entities(self, query=""):
        needle = query.lower().strip()
        entities = self.snapshot["entities"]
        if needle:
            entities = [item for item in entities if needle in (item["name"] + " " + item["label"] + " " + item["description"]).lower()]
        return [{key: item[key] for key in ("name", "label", "description", "provenance")} for item in entities]

    def entity(self, name):
        return self._entities.get(name)

    def relationships(self, entity=None):
        relationships = self.snapshot["relationships"]
        if entity:
            relationships = [item for item in relationships if entity in (item["from_entity"], item["to_entity"])]
        return relationships
