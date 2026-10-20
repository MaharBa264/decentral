"""Verified mapping of normalized key/index metadata; never parses definitions."""
from decentral.catalog.schema import CatalogValidationError


def apply_constraints(relations, primary_keys, foreign_keys, indexes, provenance):
    lookup = {(r["schema"], r["name"]): r for r in relations}
    for rows, kind in ((primary_keys, "pk"), (foreign_keys, "fk"), (indexes, "index")):
        for row in rows:
            if type(row.get("position")) is not int or row["position"] < 1: raise CatalogValidationError("%s position is incomplete" % kind)
            if (row.get("schema"), row.get("relation")) not in lookup: raise CatalogValidationError("%s relation is unknown" % kind)
    groups = {}
    for row in primary_keys:
        groups.setdefault((row["schema"],row["relation"],row["name"]),[]).append(row)
    for (schema,relation,name), rows in groups.items():
        rows=sorted(rows,key=lambda r:r["position"])
        if [r["position"] for r in rows] != list(range(1,len(rows)+1)): raise CatalogValidationError("primary key positions are incomplete")
        target=lookup[(schema,relation)]
        if target["primary_key"] is not None: raise CatalogValidationError("multiple primary keys")
        target["primary_key"]={"name":name,"columns":[r["column_name"] for r in rows],"provenance":provenance}
    groups={}
    for row in foreign_keys: groups.setdefault((row["schema"],row["relation"],row["name"]),[]).append(row)
    for (schema,relation,name), rows in groups.items():
        rows=sorted(rows,key=lambda r:r["position"])
        if [r["position"] for r in rows] != list(range(1,len(rows)+1)) or len({(r.get("ref_schema"),r.get("ref_relation")) for r in rows}) != 1: raise CatalogValidationError("foreign key mapping is incomplete")
        target=lookup[(schema,relation)]; target["foreign_keys"].append({"name":name,"columns":[r["column_name"] for r in rows],"ref_schema":rows[0]["ref_schema"],"ref_relation":rows[0]["ref_relation"],"ref_columns":[r["ref_column"] for r in rows],"provenance":provenance})
    groups={}
    for row in indexes: groups.setdefault((row["schema"],row["relation"],row["name"]),[]).append(row)
    for (schema,relation,name), rows in groups.items():
        rows=sorted(rows,key=lambda r:r["position"])
        if [r["position"] for r in rows] != list(range(1,len(rows)+1)) or type(rows[0].get("unique")) is not bool: raise CatalogValidationError("index mapping is incomplete")
        lookup[(schema,relation)]["indexes"].append({"name":name,"columns":[r["column_name"] for r in rows],"unique":rows[0]["unique"],"provenance":provenance})
    return relations
