"""Shared test fixtures for OpenRoast backend tests."""

from __future__ import annotations

import pytest

from openroast.core.session import RoastSession


@pytest.fixture
def session() -> RoastSession:
    """A fresh RoastSession in IDLE state."""
    return RoastSession(machine_name="test-machine")


@pytest.fixture
def monitoring_session(session: RoastSession) -> RoastSession:
    """A RoastSession in MONITORING state."""
    session.start_monitoring()
    return session


@pytest.fixture
def recording_session(monitoring_session: RoastSession) -> RoastSession:
    """A RoastSession in RECORDING state."""
    monitoring_session.start_recording()
    return monitoring_session
