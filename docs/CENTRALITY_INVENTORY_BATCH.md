# Batería de inventario PostgreSQL 9.6

Alcance: sólo `pg_catalog` e `information_schema`, filtrado a `nspname = 'centrality'`; no consulta filas operativas. Cada sentencia debe incorporarse a una definición de lote y al registro de aprobaciones del ejecutor con su SHA-256 antes de ejecutarse. El orden es determinista y cada página usa `LIMIT 250 OFFSET :offset`.

1. Conteos: `SELECT 'relations' AS kind, count(*) AS total FROM information_schema.tables WHERE table_schema='centrality' LIMIT 1;` Repetir para `columns`, `table_constraints` (PK), `referential_constraints` (FK) y `pg_indexes`.
2. Relaciones: `SELECT table_schema AS schema, table_name AS name, CASE WHEN table_type='VIEW' THEN 'view' ELSE 'table' END AS kind, '' AS description FROM information_schema.tables WHERE table_schema='centrality' ORDER BY table_schema,table_name LIMIT 250 OFFSET :offset;`
3. Columnas: `SELECT table_schema AS schema, table_name AS relation, column_name AS name, data_type AS type, is_nullable='YES' AS nullable, '' AS description FROM information_schema.columns WHERE table_schema='centrality' ORDER BY table_schema,table_name,ordinal_position LIMIT 250 OFFSET :offset;`
4. PK/FK/índices: usar `information_schema.table_constraints`, `key_column_usage`, `referential_constraints` y `pg_catalog.pg_index`/`pg_attribute`, siempre ordenados por esquema, relación, nombre y posición.

La fase de conteos fija el número exacto de páginas. El pipeline concatena únicamente páginas con cabeceras idénticas y conserva la procedencia por consulta; el operador debe comparar las cantidades agregadas con los conteos aprobados antes de declarar cobertura completa. Con el límite de 20 consultas por lote, inventarios mayores se ejecutan en lotes consecutivos y se conservan todos sus manifiestos privados.

Impacto: lectura de metadatos del esquema completo; no escribe, no altera autenticación y no expone puertos. Estado: **preparado, no ejecutado** — falta aprobación explícita de SQL y hashes.

## Lote ejecutable de la primera página

[`queries/centrality_inventory_page_001.json`](../queries/centrality_inventory_page_001.json) contiene SQL ejecutable con `OFFSET 0`, incluida la consulta `schemas_p001` exigida por el conversor. Los SHA-256 que el aprobador debe copiar, sin modificar SQL, al registro privado de aprobaciones son:

```
schemas_p001      7399c9298f09b0ccc8abf97d3f87e86eb228a306d56dd067b2724c77396abb08
relations_p001    ea820c1d22d51ae9b8cd36aa945349001361e9311c0473827697477241c1695d
columns_p001      1eb6a40b3d45e6b56c41ce94597b9204275a4c56b6d9b0a9c13061850284c16a
primary_keys_p001 5905798c2ff5725884f38d2afefa6ebb977b8dafa54e3cbeca1f9f9b3535fce8
foreign_keys_p001 1c2d0a5d3d2b0a8a907a0b12fbe1c9abedb258d825cf45183dde4ac704dbbb69
indexes_p001      5c4323aac8b9cca20e939eda9eff05b0bfdceea657d92118b4c89b270ad4cdc4
```

Procedimiento: el aprobador crea localmente entradas `{id, sha256}` en el registro privado; ejecuta el validador del extractor contra ambos archivos; conserva manifiesto y JSON/XLSX fuera de Git; después usa sus conteos para generar páginas con offsets 250, 500, etc. Un piloto requiere una lista aprobada de relaciones: no se eligieron nombres ni se ejecutó SQL aquí.
