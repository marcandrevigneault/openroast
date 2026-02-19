"""Thermal simulation engine for roaster machines.

Provides a simple first-order thermal model that produces realistic
BT/ET temperature curves based on burner, airflow, and drum settings.
"""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class ThermalState:
    """Current state of the thermal simulation."""

    bt: float = 25.0
    et: float = 25.0
    burner: float = 0.0
    airflow: float = 50.0
    drum: float = 50.0
    ambient: float = 25.0


# Thermal model constants
_MAX_BURNER_HEAT = 8.0  # °C/s at 100% burner
_AIRFLOW_COOLING = 0.03  # cooling coefficient per % airflow
_ET_TO_BT_TRANSFER = 0.015  # heat transfer rate ET → BT per second
_AMBIENT_LOSS = 0.002  # heat loss to ambient per second
_NOISE_STDDEV = 0.3  # °C noise standard deviation
_MAX_TEMP = 350.0
_MIN_TEMP = 0.0


class ThermalEngine:
    """Simulates roaster thermal behaviour.

    Call :meth:`step` at regular intervals to advance the simulation.
    The engine accepts control inputs (burner, airflow, drum) and
    produces updated BT/ET values.

    Args:
        seed: Optional RNG seed for deterministic testing.
    """

    def __init__(self, seed: int | None = None) -> None:
        self.state = ThermalState()
        self._rng = random.Random(seed)

    def set_control(self, channel: str, value: float) -> None:
        """Update a control input.

        Args:
            channel: Control channel name ("burner", "air", "drum", etc.).
            value: Raw control value in native units.
        """
        name = channel.lower()
        if name in ("burner", "gas", "gas1", "gas2", "heater", "power", "slider1"):
            self.state.burner = value
        elif name in ("air", "airflow", "fan", "cooling", "cooling_air", "slider2"):
            self.state.airflow = value
        elif name in ("drum", "slider4"):
            self.state.drum = value

    def step(self, dt: float = 1.0) -> ThermalState:
        """Advance the simulation by ``dt`` seconds.

        Args:
            dt: Time step in seconds.

        Returns:
            Updated thermal state.
        """
        s = self.state

        # Heat input from burner (scaled 0-100%)
        burner_frac = max(0.0, min(100.0, s.burner)) / 100.0
        heat_input = _MAX_BURNER_HEAT * burner_frac * dt

        # Cooling from airflow
        airflow_frac = max(0.0, min(100.0, s.airflow)) / 100.0
        cooling = _AIRFLOW_COOLING * airflow_frac * (s.et - s.ambient) * dt

        # Ambient heat loss
        ambient_loss = _AMBIENT_LOSS * (s.et - s.ambient) * dt

        # ET update: gains heat from burner, loses to airflow and ambient
        s.et += heat_input - cooling - ambient_loss

        # BT follows ET with thermal lag (first-order transfer)
        bt_transfer = _ET_TO_BT_TRANSFER * (s.et - s.bt) * dt
        s.bt += bt_transfer

        # Add noise
        s.et += self._rng.gauss(0, _NOISE_STDDEV)
        s.bt += self._rng.gauss(0, _NOISE_STDDEV)

        # Clamp to valid range
        s.et = max(_MIN_TEMP, min(_MAX_TEMP, s.et))
        s.bt = max(_MIN_TEMP, min(_MAX_TEMP, s.bt))

        return s
