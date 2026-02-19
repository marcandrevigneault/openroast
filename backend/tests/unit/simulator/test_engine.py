"""Tests for the thermal simulation engine."""

from __future__ import annotations

from openroast.simulator.engine import ThermalEngine, ThermalState


class TestThermalState:
    """Tests for ThermalState defaults."""

    def test_defaults(self) -> None:
        state = ThermalState()
        assert state.bt == 25.0
        assert state.et == 25.0
        assert state.burner == 0.0
        assert state.airflow == 50.0
        assert state.drum == 50.0
        assert state.ambient == 25.0


class TestThermalEngine:
    """Tests for ThermalEngine."""

    def test_no_heat_stays_near_ambient(self) -> None:
        """With no burner, temperatures should stay near ambient."""
        engine = ThermalEngine(seed=42)
        engine.state.burner = 0.0
        engine.state.airflow = 0.0
        engine.state.et = 25.0
        engine.state.bt = 25.0

        for _ in range(10):
            engine.step(dt=1.0)

        # Should stay near ambient (±noise)
        assert abs(engine.state.et - 25.0) < 5.0
        assert abs(engine.state.bt - 25.0) < 5.0

    def test_burner_heats_et(self) -> None:
        """ET should increase when burner is on."""
        engine = ThermalEngine(seed=42)
        engine.state.burner = 80.0
        engine.state.airflow = 0.0

        initial_et = engine.state.et
        for _ in range(60):
            engine.step(dt=1.0)

        assert engine.state.et > initial_et + 50

    def test_bt_follows_et_with_lag(self) -> None:
        """BT should increase but lag behind ET."""
        engine = ThermalEngine(seed=42)
        engine.state.burner = 100.0
        engine.state.airflow = 0.0

        for _ in range(120):
            engine.step(dt=1.0)

        # Both should be well above ambient
        assert engine.state.et > 100
        assert engine.state.bt > 50
        # ET should lead BT
        assert engine.state.et > engine.state.bt

    def test_airflow_cools(self) -> None:
        """Higher airflow should cool faster."""
        # Start hot with burner off
        engine_low = ThermalEngine(seed=42)
        engine_low.state.et = 250.0
        engine_low.state.bt = 200.0
        engine_low.state.burner = 0.0
        engine_low.state.airflow = 20.0

        engine_high = ThermalEngine(seed=42)
        engine_high.state.et = 250.0
        engine_high.state.bt = 200.0
        engine_high.state.burner = 0.0
        engine_high.state.airflow = 100.0

        for _ in range(30):
            engine_low.step(dt=1.0)
            engine_high.step(dt=1.0)

        # High airflow should cool ET more
        assert engine_high.state.et < engine_low.state.et

    def test_set_control_burner(self) -> None:
        engine = ThermalEngine(seed=42)
        engine.set_control("burner", 75.0)
        assert engine.state.burner == 75.0

    def test_set_control_aliases(self) -> None:
        """Various channel names should map to the right thermal input."""
        engine = ThermalEngine(seed=42)

        engine.set_control("gas", 80.0)
        assert engine.state.burner == 80.0

        engine.set_control("air", 60.0)
        assert engine.state.airflow == 60.0

        engine.set_control("fan", 40.0)
        assert engine.state.airflow == 40.0

        engine.set_control("drum", 55.0)
        assert engine.state.drum == 55.0

    def test_temperature_clamped(self) -> None:
        """Temperatures should never exceed bounds."""
        engine = ThermalEngine(seed=42)
        engine.state.burner = 100.0
        engine.state.airflow = 0.0

        for _ in range(10000):
            engine.step(dt=1.0)

        assert engine.state.et <= 350.0
        assert engine.state.bt <= 350.0
        assert engine.state.et >= 0.0
        assert engine.state.bt >= 0.0

    def test_deterministic_with_seed(self) -> None:
        """Same seed should produce same results."""
        engine1 = ThermalEngine(seed=123)
        engine1.state.burner = 50.0
        engine2 = ThermalEngine(seed=123)
        engine2.state.burner = 50.0

        for _ in range(20):
            engine1.step(dt=1.0)
            engine2.step(dt=1.0)

        assert engine1.state.et == engine2.state.et
        assert engine1.state.bt == engine2.state.bt

    def test_step_returns_state(self) -> None:
        engine = ThermalEngine(seed=42)
        result = engine.step(dt=1.0)
        assert isinstance(result, ThermalState)
        assert result is engine.state
