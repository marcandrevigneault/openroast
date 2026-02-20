"""Pydantic models for saved roast schedules."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SavedSchedule(BaseModel):
    """A saved roast schedule — trigger/action steps for automation replay."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(description="Schedule display name")
    machine_name: str = Field(default="", description="Machine this was created for")
    created_at: datetime = Field(default_factory=datetime.now)
    steps: list[dict] = Field(
        default_factory=list,
        description="ScheduleStep dicts (trigger + actions + enabled)",
    )
    source_profile_name: str | None = Field(
        default=None, description="Profile this schedule was imported from"
    )
