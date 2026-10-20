# Arquitectura H0

```
fixture sintético JSON -> validador estricto -> CatalogRepository -> API HTTP read-only -> UI estática
                               ^
                    contrato CatalogExtractor (futuro, sin implementar)
```

El snapshot tiene formato `decentral.catalog/v1`, identificador, fecha, fuente, hash SHA-256, entidades, columnas, índices y relaciones. Cada elemento de dominio lleva procedencia: `declarada`, `corroborada` o `hipotesis`, fuente y evidencia. La validación rechaza claves inesperadas, referencias inválidas, hashes alterados y cargas superiores a 1 MiB.

El API expone `GET /api/catalog`, `GET /api/entities?query=`, `GET /api/entities/{name}` y `GET /api/relationships?entity=`. La única ruta de importación, `POST /api/import/local`, valida sin guardar. No hay endpoint SQL.

El contenedor usa filesystem de solo lectura, tmpfs para `/tmp`, sin capacidades Linux y sin publicación de puertos por defecto. Un despliegue futuro podría incorporar un proxy independiente dentro de la red Docker.

## Dependencias inspeccionadas

No hay una integración con sistemas externos en este árbol. No se han supuesto rutas, APIs ni formatos. La integración permanece como contrato hasta que se facilite un formato de entrada autorizado.
