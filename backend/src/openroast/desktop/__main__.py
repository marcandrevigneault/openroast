"""Entry point for the desktop application."""

import sys

if sys.platform == "darwin":
    from openroast.desktop.menubar import main
else:
    from openroast.desktop.tray_windows import main

if __name__ == "__main__":
    main()
