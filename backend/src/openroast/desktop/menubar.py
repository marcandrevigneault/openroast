"""macOS menu bar application for OpenRoast.

Provides a system tray icon with controls to start/stop the server
and open the web UI in the default browser.
"""

from __future__ import annotations

import logging
import sys
import threading
import webbrowser
from pathlib import Path

import rumps
import uvicorn

logger = logging.getLogger(__name__)

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8080


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
            ],
        )
        self._server: uvicorn.Server | None = None
        self._server_thread: threading.Thread | None = None
        self._host = DEFAULT_HOST
        self._port = DEFAULT_PORT
        self._started = False

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
        from openroast.main import app as fastapi_app

        config = uvicorn.Config(
            fastapi_app,
            host=self._host,
            port=self._port,
            log_level="info",
        )
        self._server = uvicorn.Server(config)
        self._server.run()

    def _start_server(self) -> None:
        """Start the server in a background thread and open the browser."""
        self._server_thread = threading.Thread(target=self._run_server, daemon=True)
        self._server_thread.start()

        def _open_after_delay() -> None:
            self.menu["Server: Starting..."].title = (
                f"Server: Running ({self._port})"
            )
            self._started = True
            webbrowser.open(f"http://127.0.0.1:{self._port}")

        threading.Timer(1.5, _open_after_delay).start()

    def _stop_server(self) -> None:
        """Signal the server to shut down."""
        if self._server:
            self._server.should_exit = True
        if self._server_thread:
            self._server_thread.join(timeout=5)


def main() -> None:
    """Entry point for the menu bar application."""
    app = OpenRoastApp()
    # Start server before entering the rumps run loop
    app._start_server()
    app.run()


if __name__ == "__main__":
    main()
