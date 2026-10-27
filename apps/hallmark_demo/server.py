"""Loopback-only HTTP transport. Both interfaces use this API."""

import json
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .engine import RunManager, parse_json

WEB = Path(__file__).parent / "web"


class DemoServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, root, port=8765):
        self.token = secrets.token_urlsafe(32)
        self.manager = None
        super().__init__(("127.0.0.1", port), Handler)
        self.origin = f"http://127.0.0.1:{self.server_port}"
        try:
            self.manager = RunManager(root)
            files = {
                "": (WEB / "index.html", "text/html; charset=utf-8"),
                "app.js": (WEB / "app.js", "text/javascript; charset=utf-8"),
                "style.css": (WEB / "style.css", "text/css; charset=utf-8"),
                "mark.svg": (self.manager.root / "website/assets/mark.svg", "image/svg+xml"),
            }
            for font in ("public-sans", "newsreader"):
                files[f"{font}.woff2"] = (
                    self.manager.root / f"website/assets/fonts/{font}.woff2",
                    "font/woff2",
                )
            self.assets = {
                name: (path.read_bytes(), mime)
                for name, (path, mime) in files.items()
                if path.is_file()
            }

        except BaseException:
            self.server_close()
            raise

    def server_close(self):
        super().server_close()
        if self.manager is not None:
            self.manager.close()
            self.manager = None


class Handler(BaseHTTPRequestHandler):
    server_version = "HallmarkDemo/1"

    def log_message(self, *_args):
        pass

    def _reply(self, data, status=200, content_type="application/json", filename=None):
        if not isinstance(data, bytes):
            data = json.dumps(data, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; "
            "font-src 'self'; connect-src 'self'; frame-ancestors 'none'; "
            "base-uri 'none'; form-action 'self'",
        )
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _allowed(self):
        port = self.server.server_port
        if self.headers.get("Host") not in {f"127.0.0.1:{port}", f"localhost:{port}"}:
            self._reply({"error": "Unrecognized host"}, 403)
            return False
        origin = self.headers.get("Origin")
        if origin and origin not in {self.server.origin, f"http://localhost:{port}"}:
            self._reply({"error": "Cross-origin requests are disabled"}, 403)
            return False
        return True

    def do_GET(self):
        if not self._allowed():
            return
        manager = self.server.manager
        parts = urlsplit(self.path).path.strip("/").split("/")
        try:
            if parts == ["api", "info"]:
                self._reply(
                    dict(
                        token=self.server.token,
                        app_revision=manager.app_revision,
                        root=str(manager.root),
                        workflows=[w.public() for w in manager.workflows.values()],
                        retained=manager.retained(),
                    )
                )
            elif parts == ["api", "runs"]:
                self._reply(manager.list())
            elif len(parts) == 3 and parts[:2] == ["api", "checks"]:
                self._reply(manager.checks(parts[2]))
            elif len(parts) == 3 and parts[:2] == ["api", "runs"]:
                self._reply(manager.snapshot(parts[2]))
            elif len(parts) == 4 and parts[:2] == ["api", "runs"] and parts[3] == "receipt":
                self._reply(
                    json.dumps(manager.receipt(parts[2])).encode(),
                    filename=f"hallmark-{parts[2]}.json",
                )
            elif len(parts) == 5 and parts[:2] == ["api", "runs"] and parts[3] == "artifacts":
                data, name = manager.artifact(parts[2], parts[4])
                self._reply(data, content_type="application/json", filename=name)
            else:
                item = self.server.assets.get("/".join(parts))
                if item is None:
                    raise KeyError("Not found")
                self._reply(item[0], content_type=item[1])
        except KeyError:
            self._reply({"error": "Not found"}, 404)
        except (OSError, ValueError, RecursionError) as error:
            self._reply({"error": manager.redact(error)}, 400)

    def do_POST(self):
        if not self._allowed():
            return
        manager = self.server.manager
        if not secrets.compare_digest(self.headers.get("X-Hallmark-Token", ""), self.server.token):
            self._reply({"error": "Missing or invalid local session token"}, 403)
            return
        try:
            if self.headers.get("Content-Type") != "application/json":
                raise ValueError("Content-Type must be application/json")
            length = int(self.headers.get("Content-Length", "-1"))
            if not 0 < length <= 16384:
                raise ValueError("Request must be 1–16384 bytes")
            data = parse_json(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("Expected an object")
            parts = urlsplit(self.path).path.strip("/").split("/")
            if parts == ["api", "runs"]:
                if set(data) != {"workflow", "parameters"} or not isinstance(data["workflow"], str):
                    raise ValueError("Expected workflow and parameters")
                result = manager.start(data["workflow"], data["parameters"])
            elif len(parts) == 4 and parts[:2] == ["api", "runs"] and parts[3] == "cancel":
                if data:
                    raise ValueError("Cancel takes an empty object")
                result = manager.cancel(parts[2])
            else:
                raise KeyError("Not found")
            self._reply(result, 202)
        except KeyError:
            self._reply({"error": "Not found"}, 404)
        except (OSError, ValueError, RecursionError) as error:
            self._reply({"error": manager.redact(error)}, 400)
