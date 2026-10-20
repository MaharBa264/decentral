# Batería de inventario PostgreSQL 9.6

Alcance: sólo `pg_catalog` e `information_schema`, filtrado a `nspname = 'centrality'`; no consulta filas operativas. Cada sentencia debe incorporarse a una definición de lote y al registro de aprobaciones del ejecutor con su SHA-256 antes de ejecutarse. El orden es determinista y cada página usa `LIMIT 250 OFFSET :offset`.

1. Conteos: `SELECT 'relations' AS kind, count(*) AS total FROM information_schema.tables WHERE table_schema='centrality' LIMIT 1;` Repetir para `columns`, `table_constraints` (PK), `referential_constraints` (FK) y `pg_indexes`.
2. Relaciones: `SELECT table_schema AS schema, table_name AS name, CASE WHEN table_type='VIEW' THEN 'view' ELSE 'table' END AS kind, '' AS description FROM information_schema.tables WHERE table_schema='centrality' ORDER BY table_schema,table_name LIMIT 250 OFFSET :offset;`
3. Columnas: `SELECT table_schema AS schema, table_name AS relation, column_name AS name, data_type AS type, is_nullable='YES' AS nullable, '' AS description FROM information_schema.columns WHERE table_schema='centrality' ORDER BY table_schema,table_name,ordinal_position LIMIT 250 OFFSET :offset;`
4. PK/FK/índices: usar `information_schema.table_constraints`, `key_column_usage`, `referential_constraints` y `pg_catalog.pg_index`/`pg_attribute`, siempre ordenados por esquema, relación, nombre y posición.

La fase de conteos fija el número exacto de páginas. El pipeline concatena únicamente páginas con cabeceras idénticas y conserva la procedencia por consulta; el operador debe comparar las cantidades agregadas con los conteos aprobados antes de declarar cobertura completa. Con el límite de 20 consultas por lote, inventarios mayores se ejecutan en lotes consecutivos y se conservan todos sus manifiestos privados.

Impacto: lectura de metadatos del esquema completo; no escribe, no altera autenticación y no expone puertos. Estado: **preparado, no ejecutado** — falta aprobación explícita de SQL y hashes.
