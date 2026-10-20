"""Small dependency-free read-only HTTP API and static frontend server."""
import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from urllib.parse import parse_qs, urlparse

from decentral.catalog.repository import CatalogRepository
from decentral.catalog.schema import CatalogValidationError, MAX_SNAPSHOT_BYTES
from decentral.importers.local_loader import load_snapshot_bytes


STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class DecentralHandler(BaseHTTPRequestHandler):
    repository = None

    def log_message(self, format, *args):
        # Avoid logging query values or imported content.
        return

    def _send_json(self, status, body):
        encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(encoded)

    def _static(self, filename, content_type):
        path = os.path.join(STATIC_DIR, filename)
        with open(path, "rb") as handle:
            content = handle.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/catalog":
            return self._send_json(200, self.repository.metadata())
        if parsed.path == "/api/entities":
            query = parse_qs(parsed.query).get("query", [""])[0]
            return self._send_json(200, {"entities": self.repository.list_entities(query)})
        if parsed.path.startswith("/api/entities/"):
            entity = self.repository.entity(parsed.path.rsplit("/", 1)[-1])
            return self._send_json(200, entity) if entity else self._send_json(404, {"error": "entity not found"})
        if parsed.path == "/api/relationships":
            entity = parse_qs(parsed.query).get("entity", [None])[0]
            return self._send_json(200, {"relationships": self.repository.relationships(entity)})
        if parsed.path in ("/", "/index.html"):
            return self._static("index.html", "text/html; charset=utf-8")
        if parsed.path == "/app.js":
            return self._static("app.js", "application/javascript; charset=utf-8")
        if parsed.path == "/styles.css":
            return self._static("styles.css", "text/css; charset=utf-8")
        return self._send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/api/import/local":
            return self._send_json(404, {"error": "not found"})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size <= 0:
                raise CatalogValidationError("empty imports are not accepted")
            if size > MAX_SNAPSHOT_BYTES:
                raise CatalogValidationError("snapshot exceeds the 1 MiB local import limit")
            snapshot = load_snapshot_bytes(self.rfile.read(size))
        except (ValueError, CatalogValidationError) as error:
            return self._send_json(400, {"error": str(error)})
        # Deliberately validate only: persistence and source-system integration are later work.
        return self._send_json(202, {"accepted": True, "snapshot_id": snapshot["snapshot_id"]})


def load_repository(path):
    with open(path, "rb") as handle:
        return CatalogRepository(load_snapshot_bytes(handle.read()))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--snapshot", required=True)
    args = parser.parse_args()
    DecentralHandler.repository = load_repository(args.snapshot)
    server = ThreadingHTTPServer((args.host, args.port), DecentralHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()
