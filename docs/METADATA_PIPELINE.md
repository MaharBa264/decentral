# Pipeline local H1

`convert_batch` acepta sólo un lote ya autorizado y terminado. Verifica manifiesto v1, estados, fechas ISO, cobertura, hashes SHA-256, identificadores de consulta y conteos de filas; rechaza errores, rutas inseguras y truncamiento.

Las consultas requeridas son `schemas`, `relations` y `columns`. PK, FK e índices quedan `not_investigated` hasta disponer de una asignación aprobada: el conversor no los infiere. La carga HTTP sigue limitada a 1 MiB; el arranque acepta un snapshot local explícito de hasta 50 MiB mediante `load_snapshot_file`.
