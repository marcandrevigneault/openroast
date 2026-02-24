"""Tests for openroast.core.paths."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

from openroast.core.paths import get_bundle_root, get_data_root, is_bundled


class TestIsBundled:
    def test_not_bundled_in_normal_env(self) -> None:
        assert is_bundled() is False

    def test_bundled_when_frozen(self) -> None:
        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "_MEIPASS", "/tmp/bundle", create=True),
        ):
            assert is_bundled() is True

    def test_not_bundled_when_frozen_but_no_meipass(self) -> None:
        with patch.object(sys, "frozen", True, create=True):
            if hasattr(sys, "_MEIPASS"):
                with patch.object(sys, "_MEIPASS", create=True):
                    delattr(sys, "_MEIPASS")
                    assert is_bundled() is False
            else:
                assert is_bundled() is False


class TestGetDataRoot:
    def test_dev_returns_backend_data_dir(self) -> None:
        root = get_data_root()
        assert root.name == "data"
        assert "openroast" in str(root)

    def test_bundled_macos_returns_app_support_dir(self) -> None:
        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "_MEIPASS", "/tmp/bundle", create=True),
            patch.object(sys, "platform", "darwin"),
        ):
            root = get_data_root()
            assert root == Path.home() / "Library" / "Application Support" / "OpenRoast"

    def test_bundled_windows_returns_local_appdata(self) -> None:
        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "_MEIPASS", "C:\\tmp\\bundle", create=True),
            patch.object(sys, "platform", "win32"),
            patch.dict("os.environ", {"LOCALAPPDATA": "C:\\Users\\test\\AppData\\Local"}),
        ):
            root = get_data_root()
            assert root == Path("C:\\Users\\test\\AppData\\Local") / "OpenRoast"

    def test_bundled_windows_fallback_without_env(self) -> None:
        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "_MEIPASS", "C:\\tmp\\bundle", create=True),
            patch.object(sys, "platform", "win32"),
            patch.dict("os.environ", {}, clear=True),
        ):
            root = get_data_root()
            assert root == Path.home() / "AppData" / "Local" / "OpenRoast"

    def test_bundled_linux_returns_xdg_data(self) -> None:
        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "_MEIPASS", "/tmp/bundle", create=True),
            patch.object(sys, "platform", "linux"),
        ):
            root = get_data_root()
            assert root == Path.home() / ".local" / "share" / "openroast"


class TestGetBundleRoot:
    def test_dev_returns_none(self) -> None:
        assert get_bundle_root() is None

    def test_bundled_returns_meipass(self) -> None:
        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "_MEIPASS", "/tmp/bundle", create=True),
        ):
            assert get_bundle_root() == Path("/tmp/bundle")
