# Consultas PostgreSQL 9.6 autorizables

La batería debe registrarse en el archivo de aprobaciones del ejecutor antes de ejecutarse. Todas son `SELECT`, con filtros por esquemas permitidos y `LIMIT` explícito.

```sql
SELECT n.nspname AS schema FROM pg_catalog.pg_namespace n WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname <> 'information_schema' ORDER BY 1 LIMIT 250;
SELECT table_schema AS schema, table_name AS name, CASE WHEN table_type = 'VIEW' THEN 'view' ELSE 'table' END AS kind, '' AS description FROM information_schema.tables WHERE table_schema = ANY (ARRAY['public']) ORDER BY 1,2 LIMIT 250;
SELECT table_schema AS schema, table_name AS relation, column_name AS name, data_type AS type, is_nullable = 'YES' AS nullable, '' AS description FROM information_schema.columns WHERE table_schema = ANY (ARRAY['public']) ORDER BY 1,2,ordinal_position LIMIT 250;
```

La lista de esquemas permitidos debe ser sustituida localmente por una aprobación explícita. Para PK, FK e índices se requieren consultas separadas y aprobadas; no se infieren desde columnas.
