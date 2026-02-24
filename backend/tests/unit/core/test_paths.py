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

    def test_bundled_returns_app_support_dir(self) -> None:
        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "_MEIPASS", "/tmp/bundle", create=True),
        ):
            root = get_data_root()
            assert root == Path.home() / "Library" / "Application Support" / "OpenRoast"


class TestGetBundleRoot:
    def test_dev_returns_none(self) -> None:
        assert get_bundle_root() is None

    def test_bundled_returns_meipass(self) -> None:
        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "_MEIPASS", "/tmp/bundle", create=True),
        ):
            assert get_bundle_root() == Path("/tmp/bundle")
