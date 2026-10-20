FROM python:3.12-alpine

WORKDIR /app
COPY decentral /app/decentral
COPY catalog /app/catalog

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8080
CMD ["python", "-m", "decentral.web.server", "--host", "0.0.0.0", "--port", "8080", "--snapshot", "/app/catalog/synthetic-demo.json"]
