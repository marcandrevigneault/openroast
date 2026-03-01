"""macOS menu bar application for OpenRoast.

Provides a system tray icon with controls to start/stop the server
and open the web UI in the default browser.
"""

from __future__ import annotations

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

import rumps
import uvicorn

logger = logging.getLogger(__name__)

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8080

_SERVER_READY_TIMEOUT = 30  # seconds
_POLL_INTERVAL = 0.5  # seconds


def _setup_logging() -> None:
    """Configure file logging so startup errors are diagnosable."""
    log_dir = Path.home() / "Library" / "Application Support" / "OpenRoast"
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


class OpenRoastApp(rumps.App):
    """Menu bar application for OpenRoast."""

    def __init__(self) -> None:
        super().__init__(
            name="OpenRoast",
            icon=self._resolve_icon(),
            menu=[
                "Open in Browser",
                None,
                rumps.MenuItem("Server: Starting...", callback=None),
                None,
                rumps.MenuItem("Quit", callback=self._on_quit),
            ],
            quit_button=None,
        )
        self._server: uvicorn.Server | None = None
        self._server_thread: threading.Thread | None = None
        self._host = DEFAULT_HOST
        self._port = DEFAULT_PORT

    @staticmethod
    def _resolve_icon() -> str | None:
        """Find the menu bar icon."""
        candidates = [
            Path(getattr(sys, "_MEIPASS", "")) / "icon.png",
            Path(__file__).parent / "icon.png",
        ]
        for p in candidates:
            if p.exists():
                return str(p)
        return None

    @rumps.clicked("Open in Browser")
    def open_browser(self, _sender: rumps.MenuItem) -> None:
        """Open the OpenRoast UI in the default browser."""
        webbrowser.open(f"http://127.0.0.1:{self._port}")

    def _run_server(self) -> None:
        """Run the uvicorn server (blocking, called in background thread)."""
        try:
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
            self.menu["Server: Starting..."].title = "Server: Error (see logs)"

    def _wait_and_open_browser(self) -> None:
        """Poll /health until the server is ready, then open the browser."""
        url = f"http://127.0.0.1:{self._port}/health"
        attempts = int(_SERVER_READY_TIMEOUT / _POLL_INTERVAL)
        for _ in range(attempts):
            time.sleep(_POLL_INTERVAL)
            try:
                with urllib.request.urlopen(url, timeout=1) as resp:
                    if resp.status == 200:
                        self.menu["Server: Starting..."].title = (
                            f"Server: Running ({self._port})"
                        )
                        webbrowser.open(f"http://127.0.0.1:{self._port}")
                        return
            except Exception:
                continue
        logger.error("Server did not become ready within %ds", _SERVER_READY_TIMEOUT)
        self.menu["Server: Starting..."].title = "Server: Failed to start"

    def _start_server(self) -> None:
        """Start the server in a background thread and open the browser."""
        if _port_in_use(self._port):
            rumps.notification(
                title="OpenRoast",
                subtitle="Port already in use",
                message=f"Port {self._port} is busy. Is another instance running?",
            )
            self.menu["Server: Starting..."].title = "Server: Port in use"
            return

        self._server_thread = threading.Thread(target=self._run_server, daemon=True)
        self._server_thread.start()

        threading.Thread(target=self._wait_and_open_browser, daemon=True).start()

    def _on_quit(self, _sender: rumps.MenuItem) -> None:
        """Stop the server and force-quit the application."""
        self.stop_server()
        rumps.quit_application()
        # Force exit — uvicorn's event loop may keep the process alive
        # even after should_exit is set and the thread join times out.
        os._exit(0)

    def stop_server(self) -> None:
        """Signal the server to shut down."""
        if self._server:
            self._server.should_exit = True
        if self._server_thread:
            self._server_thread.join(timeout=3)
            self._server_thread = None


def main() -> None:
    """Entry point for the menu bar application."""
    _setup_logging()

    app = OpenRoastApp()

    # Ensure server shuts down on any exit
    atexit.register(app.stop_server)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

    app._start_server()
    app.run()


if __name__ == "__main__":
    main()
