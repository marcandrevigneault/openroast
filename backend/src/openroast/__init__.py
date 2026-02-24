"""OpenRoast — browser-based coffee roasting software."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("openroast")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"
