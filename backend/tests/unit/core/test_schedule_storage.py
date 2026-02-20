"""Unit tests for ScheduleStorage."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from openroast.core.schedule_storage import ScheduleStorage
from openroast.models.schedule import SavedSchedule

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def storage(tmp_path: Path) -> ScheduleStorage:
    return ScheduleStorage(tmp_path / "schedules")


def _make_schedule(name: str = "Morning Roast") -> SavedSchedule:
    return SavedSchedule(
        name=name,
        machine_name="Stratto 2.0",
        steps=[
            {
                "id": "s1",
                "trigger": {"type": "time", "timestamp_ms": 0},
                "actions": [{"channel": "burner", "value": 50}],
                "fired": False,
                "enabled": True,
            },
            {
                "id": "s2",
                "trigger": {"type": "time", "timestamp_ms": 60000},
                "actions": [{"channel": "burner", "value": 80}],
                "fired": False,
                "enabled": True,
            },
        ],
        source_profile_name="Ethiopian Light",
    )


class TestSaveAndGet:
    def test_save_returns_id(self, storage: ScheduleStorage) -> None:
        schedule_id = storage.save(_make_schedule())
        assert isinstance(schedule_id, str)
        assert len(schedule_id) > 0

    def test_get_returns_saved_schedule(self, storage: ScheduleStorage) -> None:
        schedule_id = storage.save(_make_schedule("My Schedule"))
        loaded = storage.get(schedule_id)
        assert loaded is not None
        assert loaded.name == "My Schedule"
        assert loaded.machine_name == "Stratto 2.0"
        assert len(loaded.steps) == 2

    def test_get_preserves_steps(self, storage: ScheduleStorage) -> None:
        schedule_id = storage.save(_make_schedule())
        loaded = storage.get(schedule_id)
        assert loaded is not None
        assert loaded.steps[0]["trigger"]["type"] == "time"
        assert loaded.steps[0]["actions"][0]["channel"] == "burner"
        assert loaded.steps[0]["actions"][0]["value"] == 50

    def test_get_preserves_source_profile(self, storage: ScheduleStorage) -> None:
        schedule_id = storage.save(_make_schedule())
        loaded = storage.get(schedule_id)
        assert loaded is not None
        assert loaded.source_profile_name == "Ethiopian Light"

    def test_get_nonexistent_returns_none(self, storage: ScheduleStorage) -> None:
        assert storage.get("nonexistent") is None

    def test_save_with_explicit_id(self, storage: ScheduleStorage) -> None:
        s = _make_schedule()
        s.id = "custom-id"
        schedule_id = storage.save(s)
        assert schedule_id == "custom-id"
        loaded = storage.get("custom-id")
        assert loaded is not None
        assert loaded.id == "custom-id"


class TestListAll:
    def test_empty_storage(self, storage: ScheduleStorage) -> None:
        assert storage.list_all() == []

    def test_lists_saved_schedules(self, storage: ScheduleStorage) -> None:
        storage.save(_make_schedule("Schedule A"))
        storage.save(_make_schedule("Schedule B"))
        summaries = storage.list_all()
        assert len(summaries) == 2
        names = {s["name"] for s in summaries}
        assert "Schedule A" in names
        assert "Schedule B" in names

    def test_summary_has_expected_fields(self, storage: ScheduleStorage) -> None:
        storage.save(_make_schedule("My Schedule"))
        summary = storage.list_all()[0]
        assert "id" in summary
        assert summary["name"] == "My Schedule"
        assert summary["machine_name"] == "Stratto 2.0"
        assert summary["step_count"] == 2


class TestDelete:
    def test_delete_existing(self, storage: ScheduleStorage) -> None:
        schedule_id = storage.save(_make_schedule())
        assert storage.delete(schedule_id) is True
        assert storage.get(schedule_id) is None

    def test_delete_nonexistent(self, storage: ScheduleStorage) -> None:
        assert storage.delete("nonexistent") is False
