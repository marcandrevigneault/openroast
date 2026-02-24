"""Unit tests for RoastSession lifecycle and data management."""

from __future__ import annotations

import pytest

from openroast.core.session import RoastSession, SessionState


class TestSessionLifecycle:
    """Tests for the state machine: IDLE → MONITORING → RECORDING → FINISHED."""

    def test_initial_state_is_idle(self, session: RoastSession) -> None:
        assert session.state == SessionState.IDLE

    def test_start_monitoring_from_idle(self, session: RoastSession) -> None:
        session.start_monitoring()
        assert session.state == SessionState.MONITORING

    def test_start_recording_from_monitoring(
        self, monitoring_session: RoastSession,
    ) -> None:
        monitoring_session.start_recording()
        assert monitoring_session.state == SessionState.RECORDING

    def test_stop_recording(self, recording_session: RoastSession) -> None:
        recording_session.stop_recording()
        assert recording_session.state == SessionState.FINISHED

    def test_cannot_record_from_idle(self, session: RoastSession) -> None:
        with pytest.raises(ValueError, match="Cannot start recording"):
            session.start_recording()

    def test_stop_monitoring(
        self, monitoring_session: RoastSession,
    ) -> None:
        monitoring_session.stop_monitoring()
        assert monitoring_session.state == SessionState.IDLE

    def test_cannot_stop_monitoring_from_idle(
        self, session: RoastSession,
    ) -> None:
        with pytest.raises(ValueError, match="Cannot stop monitoring"):
            session.stop_monitoring()

    def test_cannot_stop_monitoring_from_recording(
        self, recording_session: RoastSession,
    ) -> None:
        with pytest.raises(ValueError, match="Cannot stop monitoring"):
            recording_session.stop_monitoring()

    def test_cannot_stop_recording_from_monitoring(
        self, monitoring_session: RoastSession,
    ) -> None:
        with pytest.raises(ValueError, match="Cannot stop recording"):
            monitoring_session.stop_recording()

    def test_cannot_monitor_while_recording(
        self, recording_session: RoastSession,
    ) -> None:
        with pytest.raises(ValueError, match="Cannot start monitoring"):
            recording_session.start_monitoring()

    def test_can_restart_monitoring_after_finished(
        self, recording_session: RoastSession,
    ) -> None:
        recording_session.stop_recording()
        recording_session.start_monitoring()
        assert recording_session.state == SessionState.MONITORING


class TestDataRecording:
    """Tests for temperature data accumulation."""

    def test_no_data_initially(self, session: RoastSession) -> None:
        assert session.data_points == 0

    def test_monitoring_does_not_store_data(
        self, monitoring_session: RoastSession,
    ) -> None:
        monitoring_session.add_reading(0, 210.0, 155.0)
        monitoring_session.add_reading(3000, 211.0, 158.0)
        assert monitoring_session.data_points == 0

    def test_recording_stores_data(
        self, recording_session: RoastSession,
    ) -> None:
        recording_session.add_reading(0, 210.0, 155.0)
        recording_session.add_reading(3000, 211.0, 158.0)
        assert recording_session.data_points == 2

    def test_start_recording_clears_previous_data(
        self, monitoring_session: RoastSession,
    ) -> None:
        monitoring_session.start_recording()
        monitoring_session.add_reading(0, 210.0, 155.0)
        assert monitoring_session.data_points == 1
        monitoring_session.stop_recording()
        # Start a new recording
        monitoring_session.start_monitoring()
        monitoring_session.start_recording()
        assert monitoring_session.data_points == 0


class TestEvents:
    """Tests for roast event tracking."""

    def test_add_event_during_recording(
        self, recording_session: RoastSession,
    ) -> None:
        recording_session.add_event("CHARGE", 5000.0)
        recording_session.add_event("DRY", 180000.0)
        # Events are stored — verified via to_profile
        recording_session.add_reading(0, 210.0, 155.0)
        profile = recording_session.to_profile("test")
        assert len(profile.events) == 2
        assert profile.events[0].event_type == "CHARGE"
        assert profile.events[1].event_type == "DRY"

    def test_cannot_add_event_outside_recording(
        self, monitoring_session: RoastSession,
    ) -> None:
        with pytest.raises(ValueError, match="Cannot add events"):
            monitoring_session.add_event("CHARGE", 0)

    def test_auto_detected_flag(
        self, recording_session: RoastSession,
    ) -> None:
        recording_session.add_event("CHARGE", 5000.0, auto_detected=True)
        recording_session.add_reading(0, 210.0, 155.0)
        profile = recording_session.to_profile("test")
        assert profile.events[0].auto_detected is True


class TestControlTracking:
    """Tests for control value tracking."""

    def test_add_control_during_monitoring(
        self, monitoring_session: RoastSession,
    ) -> None:
        monitoring_session.add_control_change(0, "burner", 0.8)
        monitoring_session.add_control_change(5000, "airflow", 0.5)
        # Controls are stored even during monitoring
        monitoring_session.start_recording()
        # But start_recording clears them
        monitoring_session.add_reading(0, 210.0, 155.0)
        profile = monitoring_session.to_profile("test")
        assert profile.controls == {}

    def test_add_control_during_recording(
        self, recording_session: RoastSession,
    ) -> None:
        recording_session.add_control_change(0, "burner", 0.8)
        recording_session.add_control_change(5000, "burner", 0.6)
        recording_session.add_control_change(5000, "airflow", 0.5)
        recording_session.add_reading(0, 210.0, 155.0)
        profile = recording_session.to_profile("test")
        assert "burner" in profile.controls
        assert len(profile.controls["burner"]) == 2
        assert profile.controls["burner"][0] == (0, 0.8)
        assert profile.controls["burner"][1] == (5000, 0.6)
        assert profile.controls["airflow"][0] == (5000, 0.5)

    def test_controls_cleared_on_new_recording(
        self, monitoring_session: RoastSession,
    ) -> None:
        monitoring_session.start_recording()
        monitoring_session.add_control_change(0, "burner", 0.8)
        monitoring_session.add_reading(0, 210.0, 155.0)
        monitoring_session.stop_recording()
        # Start new recording
        monitoring_session.start_monitoring()
        monitoring_session.start_recording()
        monitoring_session.add_reading(0, 210.0, 155.0)
        profile = monitoring_session.to_profile("test")
        assert profile.controls == {}

    def test_control_ignored_in_idle(self, session: RoastSession) -> None:
        session.add_control_change(0, "burner", 0.5)
        # Should not raise, just silently ignored
        session.start_monitoring()
        session.start_recording()
        session.add_reading(0, 210.0, 155.0)
        profile = session.to_profile("test")
        assert profile.controls == {}


class TestProfileExport:
    """Tests for exporting session data as a RoastProfile."""

    def test_export_with_data(self, recording_session: RoastSession) -> None:
        recording_session.add_reading(0, 210.0, 155.0)
        recording_session.add_reading(3000, 211.0, 160.0)
        profile = recording_session.to_profile("My Roast")
        assert profile.name == "My Roast"
        assert profile.machine == "test-machine"
        assert len(profile.temperatures) == 2
        assert profile.temperatures[0].et == 210.0
        assert profile.temperatures[1].bt == 160.0

    def test_export_empty_raises(self, recording_session: RoastSession) -> None:
        with pytest.raises(ValueError, match="No data recorded"):
            recording_session.to_profile("empty")

    def test_machine_name_preserved(self) -> None:
        s = RoastSession(machine_name="Stratto 2.0")
        s.start_monitoring()
        s.start_recording()
        s.add_reading(0, 200.0, 150.0)
        profile = s.to_profile("test")
        assert profile.machine == "Stratto 2.0"
