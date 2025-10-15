from __future__ import annotations

import asyncio
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from backend.api import app as backend_app

BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8000
FRONTEND_HOST = "127.0.0.1"
FRONTEND_PORT = 3000
PROJECT_ROOT = Path(__file__).parent.resolve()
FRONTEND_DIR = PROJECT_ROOT / "frontend"

from hypercorn.asyncio import serve 
from hypercorn.config import Config 



class FrontendHandler(SimpleHTTPRequestHandler):
    """Serve the static frontend, falling back to index_clean.html."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("directory", str(FRONTEND_DIR))
        super().__init__(*args, **kwargs)

    def do_GET(self):  # type: ignore[override]
        if self.path in {"/", "/index.html"}:
            self.path = "/index_clean.html"
        return super().do_GET()

    def log_message(self, fmt: str, *args: object) -> None:  # pragma: no cover - dev helper
        message = fmt % args if args else fmt
        print(f"[frontend] {self.log_date_time_string()} {message}")


async def _serve_backend() -> None:
    """Run FastAPI backend with Hypercorn."""
    config = Config()
    config.bind = [f"{BACKEND_HOST}:{BACKEND_PORT}"]
    config.reload = True
    config.workers = 1
    print(f"[backend] Listening on http://{BACKEND_HOST}:{BACKEND_PORT} (reload enabled)")
    await serve(backend_app, config)


def _serve_frontend() -> ThreadingHTTPServer:
    """Start a thread-based HTTP server for the static frontend."""
    if not FRONTEND_DIR.exists():
        print(f"Frontend directory not found at {FRONTEND_DIR}", file=sys.stderr)
        sys.exit(1)

    handler = partial(FrontendHandler)
    server = ThreadingHTTPServer((FRONTEND_HOST, FRONTEND_PORT), handler)
    thread = threading.Thread(target=server.serve_forever, name="frontend-server", daemon=True)
    thread.start()
    print(
        f"[frontend] Serving {FRONTEND_DIR} on http://{FRONTEND_HOST}:{FRONTEND_PORT} "
        "(open index_clean.html if the browser does not redirect automatically)"
    )
    return server


def main() -> None:
    """Bring up both backend and frontend locally without make/uvicorn."""
    frontend_server = _serve_frontend()
    try:
        asyncio.run(_serve_backend())
    except KeyboardInterrupt:
        print("\nStopping development servers...")
    finally:
        frontend_server.shutdown()
        frontend_server.server_close()


if __name__ == "__main__":
    main()
