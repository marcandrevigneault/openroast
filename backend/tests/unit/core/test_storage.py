"""Unit tests for ProfileStorage."""

from __future__ import annotations

import pytest
from pathlib import Path

from openroast.core.storage import ProfileStorage
from openroast.models.profile import RoastProfile, TemperaturePoint


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


class TestDelete:
    def test_delete_existing(self, storage: ProfileStorage) -> None:
        profile_id = storage.save(_make_profile())
        assert storage.delete(profile_id) is True
        assert storage.get(profile_id) is None

    def test_delete_nonexistent(self, storage: ProfileStorage) -> None:
        assert storage.delete("nonexistent") is False
