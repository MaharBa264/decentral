# Roadmap

## H0 (entregado)

- Catálogo sintético validado, API de consulta y explorador responsivo.
- Contrato de adaptador y carga local efímera con límites.
- Compose aislado sin puertos publicados.

## H1

1. Documentar un formato de entrada autorizado y el tratamiento de secretos.
2. Construir un adaptador local fuera de Git que produzca snapshots sanitizados; revisar manualmente antes de compartirlos.
3. Añadir almacenamiento privado, historial de snapshots y detección de cambios, preservando anotaciones humanas.
4. Incorporar un proxy independiente en un despliegue futuro, sin exponer el servicio directamente.

## Posterior

- Navegación de vecindad escalable, filtros y diccionario colaborativo.
- Asistente local de consultas con grounding y validación. Sólo generará texto para copiar; nunca ejecutará consultas ni afirmará una ejecución inexistente.
