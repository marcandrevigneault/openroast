"""Windows system tray application for OpenRoast.

Provides a system tray icon with controls to start/stop the server
and open the web UI in the default browser.
"""

from __future__ import annotations

import asyncio
import atexit
import logging
import os
import signal
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

import pystray
import uvicorn
from PIL import Image

logger = logging.getLogger(__name__)

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8080

_SERVER_READY_TIMEOUT = 30  # seconds
_POLL_INTERVAL = 0.5  # seconds


def _setup_logging() -> None:
    """Configure file logging so startup errors are diagnosable."""
    log_dir = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "OpenRoast"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "openroast.log"

    logging.basicConfig(
        filename=str(log_path),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger.info("Logging initialised → %s", log_path)


def _port_in_use(port: int) -> bool:
    """Check if a TCP port is already bound."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def _resolve_icon() -> Image.Image:
    """Find and load the tray icon."""
    candidates = [
        Path(getattr(sys, "_MEIPASS", "")) / "icon.png",
        Path(__file__).parent / "icon.png",
    ]
    for p in candidates:
        if p.exists():
            return Image.open(p)
    # Fallback: tiny solid-colour icon
    return Image.new("RGB", (64, 64), color=(139, 90, 43))


class OpenRoastTray:
    """System tray application for OpenRoast on Windows."""

    def __init__(self) -> None:
        self._server: uvicorn.Server | None = None
        self._server_thread: threading.Thread | None = None
        self._host = DEFAULT_HOST
        self._port = DEFAULT_PORT
        self._status = "Starting..."
        self._icon: pystray.Icon | None = None

    def _build_menu(self) -> pystray.Menu:
        """Build the tray context menu."""
        return pystray.Menu(
            pystray.MenuItem("Open in Browser", self._on_open_browser),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                lambda _item: f"Server: {self._status}",
                action=None,
                enabled=False,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._on_quit),
        )

    def _on_open_browser(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        """Open the OpenRoast UI in the default browser."""
        webbrowser.open(f"http://127.0.0.1:{self._port}")

    def _on_quit(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        """Stop the server and exit."""
        self.stop_server()
        if self._icon:
            self._icon.stop()

    def _run_server(self) -> None:
        """Run the uvicorn server (blocking, called in background thread)."""
        try:
            # Windows needs the selector event-loop policy for uvicorn.
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

            from openroast.main import app as fastapi_app

            config = uvicorn.Config(
                fastapi_app,
                host=self._host,
                port=self._port,
                log_level="info",
            )
            self._server = uvicorn.Server(config)
            self._server.run()
        except Exception:
            logger.exception("Server failed to start")
            self._status = "Error (see logs)"
            if self._icon:
                self._icon.update_menu()

    def _wait_and_open_browser(self) -> None:
        """Poll /health until the server is ready, then open the browser."""
        url = f"http://127.0.0.1:{self._port}/health"
        attempts = int(_SERVER_READY_TIMEOUT / _POLL_INTERVAL)
        for _ in range(attempts):
            time.sleep(_POLL_INTERVAL)
            try:
                with urllib.request.urlopen(url, timeout=1) as resp:
                    if resp.status == 200:
                        self._status = f"Running ({self._port})"
                        if self._icon:
                            self._icon.update_menu()
                        webbrowser.open(f"http://127.0.0.1:{self._port}")
                        return
            except Exception:
                continue
        logger.error("Server did not become ready within %ds", _SERVER_READY_TIMEOUT)
        self._status = "Failed to start"
        if self._icon:
            self._icon.update_menu()

    def start_server(self) -> None:
        """Start the server in a background thread and open the browser."""
        if _port_in_use(self._port):
            logger.warning("Port %d already in use", self._port)
            self._status = "Port in use"
            return

        self._server_thread = threading.Thread(target=self._run_server, daemon=True)
        self._server_thread.start()

        threading.Thread(target=self._wait_and_open_browser, daemon=True).start()

    def stop_server(self) -> None:
        """Signal the server to shut down."""
        if self._server:
            self._server.should_exit = True
        if self._server_thread:
            self._server_thread.join(timeout=5)
            self._server_thread = None

    def run(self) -> None:
        """Start the tray icon and enter the event loop."""
        image = _resolve_icon()
        self._icon = pystray.Icon(
            name="OpenRoast",
            icon=image,
            title="OpenRoast",
            menu=self._build_menu(),
        )
        self._icon.run()


def main() -> None:
    """Entry point for the Windows tray application."""
    _setup_logging()

    app = OpenRoastTray()

    atexit.register(app.stop_server)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

    app.start_server()
    app.run()


if __name__ == "__main__":
    main()
