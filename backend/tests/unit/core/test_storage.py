"""Unit tests for ProfileStorage."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from openroast.core.storage import ProfileStorage
from openroast.models.profile import RoastProfile, TemperaturePoint

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def storage(tmp_path: Path) -> ProfileStorage:
    return ProfileStorage(tmp_path / "profiles")


def _make_profile(name: str = "Test Roast") -> RoastProfile:
    return RoastProfile(
        name=name,
        machine="Stratto 2.0",
        bean_name="Ethiopian",
        bean_weight_g=500,
        temperatures=[
            TemperaturePoint(timestamp_ms=0, et=210, bt=155),
            TemperaturePoint(timestamp_ms=3000, et=212, bt=160, et_ror=5.0, bt_ror=8.0),
        ],
    )


class TestSaveAndGet:
    def test_save_returns_id(self, storage: ProfileStorage) -> None:
        profile_id = storage.save(_make_profile())
        assert isinstance(profile_id, str)
        assert len(profile_id) > 0

    def test_get_returns_saved_profile(self, storage: ProfileStorage) -> None:
        profile_id = storage.save(_make_profile("My Roast"))
        loaded = storage.get(profile_id)
        assert loaded is not None
        assert loaded.name == "My Roast"
        assert loaded.machine == "Stratto 2.0"
        assert len(loaded.temperatures) == 2

    def test_get_preserves_ror(self, storage: ProfileStorage) -> None:
        profile_id = storage.save(_make_profile())
        loaded = storage.get(profile_id)
        assert loaded is not None
        assert loaded.temperatures[1].et_ror == 5.0
        assert loaded.temperatures[1].bt_ror == 8.0

    def test_get_nonexistent_returns_none(self, storage: ProfileStorage) -> None:
        assert storage.get("nonexistent") is None

    def test_save_with_explicit_id(self, storage: ProfileStorage) -> None:
        p = _make_profile()
        p.id = "custom-id"
        profile_id = storage.save(p)
        assert profile_id == "custom-id"
        loaded = storage.get("custom-id")
        assert loaded is not None
        assert loaded.id == "custom-id"


class TestListAll:
    def test_empty_storage(self, storage: ProfileStorage) -> None:
        assert storage.list_all() == []

    def test_lists_saved_profiles(self, storage: ProfileStorage) -> None:
        storage.save(_make_profile("Roast A"))
        storage.save(_make_profile("Roast B"))
        summaries = storage.list_all()
        assert len(summaries) == 2
        names = {s["name"] for s in summaries}
        assert "Roast A" in names
        assert "Roast B" in names

    def test_summary_has_expected_fields(self, storage: ProfileStorage) -> None:
        storage.save(_make_profile("My Roast"))
        summary = storage.list_all()[0]
        assert "id" in summary
        assert summary["name"] == "My Roast"
        assert summary["machine"] == "Stratto 2.0"
        assert summary["bean_name"] == "Ethiopian"
        assert summary["data_points"] == 2


class TestImage:
    def test_save_and_get_image(self, storage: ProfileStorage) -> None:
        profile_id = storage.save(_make_profile())
        png_data = b"\x89PNG\r\n\x1a\nfake-image-data"
        storage.save_image(profile_id, png_data)
        assert storage.get_image(profile_id) == png_data

    def test_get_image_nonexistent(self, storage: ProfileStorage) -> None:
        assert storage.get_image("nonexistent") is None

    def test_has_image_true(self, storage: ProfileStorage) -> None:
        profile_id = storage.save(_make_profile())
        storage.save_image(profile_id, b"img")
        assert storage.has_image(profile_id) is True

    def test_has_image_false(self, storage: ProfileStorage) -> None:
        profile_id = storage.save(_make_profile())
        assert storage.has_image(profile_id) is False

    def test_list_all_includes_has_image(self, storage: ProfileStorage) -> None:
        id1 = storage.save(_make_profile("With Image"))
        storage.save_image(id1, b"img")
        storage.save(_make_profile("No Image"))
        summaries = storage.list_all()
        by_name = {s["name"]: s for s in summaries}
        assert by_name["With Image"]["has_image"] is True
        assert by_name["No Image"]["has_image"] is False


class TestDelete:
    def test_delete_existing(self, storage: ProfileStorage) -> None:
        profile_id = storage.save(_make_profile())
        assert storage.delete(profile_id) is True
        assert storage.get(profile_id) is None

    def test_delete_nonexistent(self, storage: ProfileStorage) -> None:
        assert storage.delete("nonexistent") is False

    def test_delete_removes_image(self, storage: ProfileStorage) -> None:
        profile_id = storage.save(_make_profile())
        storage.save_image(profile_id, b"img")
        assert storage.has_image(profile_id) is True
        storage.delete(profile_id)
        assert storage.has_image(profile_id) is False
