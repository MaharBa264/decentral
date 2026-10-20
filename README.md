# Decentral — Hito 0

Explorador de solo lectura de un catálogo de datos. Esta primera entrega usa **exclusivamente** el fixture sintético incluido: no contiene datos, esquemas, credenciales ni resultados de sistemas externos.

## Decisión técnica

Se eligió Python estándar (API HTTP y validación) y HTML/CSS/JavaScript estático. El resultado es pequeño, mantenible, no añade dependencias de aplicación y se ejecuta encapsulado en Docker. No hay base de datos, volumen operativo ni conexión a sistemas externos.

## Ejecutar en desarrollo

Requiere Python 3.6+ para las pruebas locales o Docker para ejecutar el servicio.

```bash
python3 -m unittest discover -s tests -v
python3 -m decentral.web.server --snapshot catalog/synthetic-demo.json
```

Abrir `http://127.0.0.1:8080`. Para Docker, `docker compose up --build` crea una red aislada: el Compose no publica puertos al host por diseño. En desarrollo local, aplicar un override no versionado que publique sólo `127.0.0.1:8080:8080` si hiciera falta.

## Seguridad y datos reales

- Decentral no ejecuta SQL ni se conecta a sistemas externos; las consultas futuras se copiarán al editor web del usuario.
- `POST /api/import/local` sólo valida un snapshot en memoria y devuelve su identificador; no lo persiste ni lo registra.
- El límite es 1 MiB, UTF-8 JSON, campos exactos y SHA-256 del contenido. El esquema se valida antes de cualquier uso.
- `.gitignore` excluye capturas, cookies, XLSX/CSV/JSON de origen, directorios de carga, claves y configuración local. Nunca subas datos sensibles, secretos o salidas de un sistema externo.

## Integración posterior, sin publicar material sensible

El contrato `decentral.importers.contract.CatalogExtractor` define `to_snapshot(capture)`. Una integración futura debe recibir explícitamente el formato de entrada. El adaptador debe ejecutarse fuera de este repositorio público, transformar una captura autorizada al formato `decentral.catalog/v1`, eliminar o anonimizar todo contenido sensible y validar localmente con `load_snapshot_bytes`. Sólo un fixture sintético puede quedar versionado aquí.

Ver [arquitectura](docs/ARCHITECTURE.md) y [roadmap](docs/ROADMAP.md).
