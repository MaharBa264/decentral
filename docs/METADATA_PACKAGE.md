# Paquete de metadatos H1

`decentral.metadata-package/v1` contiene sólo metadatos de esquema: identificador, fecha, fuente, SHA-256, esquemas y relaciones (`table` o `view`). Cada relación declara columnas, PK, FK, índices y procedencia. No admite filas.

`PostgresMetadataPackageAdapter` valida el paquete y lo convierte al catálogo de sólo lectura actual. Para conservar compatibilidad H0, identifica cada entidad como `schema.relation`; una vista se conserva en la descripción hasta que el explorador tenga un tipo visual específico.

El extractor observado trabaja por lotes con definición de consultas, artefactos JSON/XLSX con hash y manifiesto de estado. Un exportador local posterior debe verificar el manifiesto y construir este paquete fuera del repositorio. No se versionan paquetes reales ni artefactos del extractor.
