from __future__ import annotations

import asyncio
import struct
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from hypercorn.asyncio import serve
from hypercorn.config import Config

from backend.api import app as backend_app

BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8000
FRONTEND_HOST = "127.0.0.1"
FRONTEND_PORT = 3000
PROJECT_ROOT = Path(__file__).parent.resolve()
FRONTEND_DIR = PROJECT_ROOT / "frontend"


def _generate_favicon() -> bytes:
    """Return a tiny 16x16 ico matching the primary brand color."""
    width = height = 16
    color = bytes([0xF2, 0x77, 0x18, 0xFF])  # BGRA for #1877F2 with full opacity
    xor_bitmap = color * (width * height)
    and_mask = b"\x00" * (((width + 31) // 32) * 4 * height)
    image_size = 40 + len(xor_bitmap) + len(and_mask)
    header = struct.pack("<HHH", 0, 1, 1)
    entry = struct.pack(
        "<BBBBHHII",
        width if width < 256 else 0,
        height if height < 256 else 0,
        0,
        0,
        1,
        32,
        image_size,
        22,
    )
    bitmap_header = struct.pack(
        "<IIIHHIIIIII",
        40,
        width,
        height * 2,
        1,
        32,
        0,
        len(xor_bitmap),
        2835,
        2835,
        0,
        0,
    )
    return header + entry + bitmap_header + xor_bitmap + and_mask


FAVICON_BYTES = _generate_favicon()


class FrontendHandler(SimpleHTTPRequestHandler):
    """Serve the static frontend, falling back to index_clean.html."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("directory", str(FRONTEND_DIR))
        super().__init__(*args, **kwargs)

    def do_GET(self):  # type: ignore[override]
        if self.path in {"/", "/index.html"}:
            self.path = "/index_clean.html"
        if self._serve_generated_favicon():
            return
        return super().do_GET()

    def do_HEAD(self):  # type: ignore[override]
        if self.path in {"/", "/index.html"}:
            self.path = "/index_clean.html"
        if self._serve_generated_favicon():
            return
        return super().do_HEAD()

    def _serve_generated_favicon(self) -> bool:
        if self.path != "/favicon.ico":
            return False
        self.send_response(200)
        self.send_header("Content-Type", "image/x-icon")
        self.send_header("Cache-Control", "public, max-age=86400")
        self.send_header("Content-Length", str(len(FAVICON_BYTES)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(FAVICON_BYTES)
        return True

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
