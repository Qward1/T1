from __future__ import annotations

import asyncio
import struct
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from hypercorn.asyncio import serve
from hypercorn.config import Config

from backend.api import app as backend_app

BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8000
PROJECT_ROOT = Path(__file__).parent.resolve()
FRONTEND_DIR = PROJECT_ROOT / "frontend"
SUPPORT_HOST = "127.0.0.1"
SUPPORT_PORT = 3000
CLIENT_HOST = "127.0.0.1"
CLIENT_PORT = 3001
SUPPORT_DIR = FRONTEND_DIR
CLIENT_DIR = FRONTEND_DIR / "client"


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


class StaticHandler(SimpleHTTPRequestHandler):
    """Serve a static directory with a predefined landing page."""

    def __init__(self, *args, directory: str, default_file: str, **kwargs) -> None:
        self._default_file = default_file
        kwargs.setdefault("directory", directory)
        super().__init__(*args, **kwargs)

    def do_GET(self) -> None:  # type: ignore[override]
        self._ensure_default_page()
        if self._serve_generated_favicon():
            return
        super().do_GET()

    def do_HEAD(self) -> None:  # type: ignore[override]
        self._ensure_default_page()
        if self._serve_generated_favicon():
            return
        super().do_HEAD()

    def _serve_generated_favicon(self) -> bool:
        parsed = urlsplit(self.path)
        if parsed.path != "/favicon.ico":
            return False
        self.send_response(200)
        self.send_header("Content-Type", "image/x-icon")
        self.send_header("Cache-Control", "public, max-age=86400")
        self.send_header("Content-Length", str(len(FAVICON_BYTES)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(FAVICON_BYTES)
        return True

    def _ensure_default_page(self) -> None:
        parsed = urlsplit(self.path)
        if parsed.path not in {"/", "/index.html"}:
            return
        default_path = f"/{self._default_file}"
        self.path = urlunsplit(("", "", default_path, parsed.query, parsed.fragment))

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


def _serve_static(label: str, host: str, port: int, directory: Path, default_file: str) -> ThreadingHTTPServer:
    """Start a thread-based HTTP server for a static directory."""
    if not directory.exists():
        print(f"{label} directory not found at {directory}", file=sys.stderr)
        sys.exit(1)

    handler = partial(StaticHandler, directory=str(directory), default_file=default_file)
    server = ThreadingHTTPServer((host, port), handler)
    thread = threading.Thread(target=server.serve_forever, name="frontend-server", daemon=True)
    thread.start()
    print(f"[{label}] Serving {directory} on http://{host}:{port}")
    return server


def main() -> None:
    """Bring up both backend and frontend locally without make/uvicorn."""
    support_server = _serve_static("support-ui", SUPPORT_HOST, SUPPORT_PORT, SUPPORT_DIR, "index_clean.html")
    client_server = _serve_static("client-ui", CLIENT_HOST, CLIENT_PORT, CLIENT_DIR, "index.html")
    try:
        asyncio.run(_serve_backend())
    except KeyboardInterrupt:
        print("\nStopping development servers...")
    finally:
        client_server.shutdown()
        client_server.server_close()
        support_server.shutdown()
        support_server.server_close()


if __name__ == "__main__":
    main()
