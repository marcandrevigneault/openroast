import { describe, it, expect } from "vitest";
import {
  createInitialState,
  processMessage,
  processControlInput,
  recordControlChange,
  formatTime,
  type MachineState,
} from "./machine";
import type { ServerMessage } from "$lib/types/ws-messages";

describe("createInitialState", () => {
  it("creates state with correct defaults", () => {
    const state = createInitialState("m1", "Test Machine");
    expect(state.machineId).toBe("m1");
    expect(state.machineName).toBe("Test Machine");
    expect(state.sessionState).toBe("idle");
    expect(state.driverState).toBe("disconnected");
    expect(state.currentTemp).toBeNull();
    expect(state.history).toEqual([]);
    expect(state.events).toEqual([]);
    expect(state.error).toBeNull();
    expect(state.controlHistory).toEqual([]);
    expect(state.currentControls).toBeNull();
    expect(state.controls).toEqual([]);
    expect(state.extraChannels).toEqual([]);
    expect(state.extraChannelHistory).toEqual([]);
    expect(state.currentExtraChannels).toEqual({});
  });

  it("accepts controls and extra channels", () => {
    const controls = [
      {
        name: "Burner",
        channel: "burner",
        min: 0,
        max: 100,
        step: 5,
        unit: "%",
      },
    ];
    const extraChannels = [{ name: "Inlet" }];
    const state = createInitialState("m1", "Test", controls, extraChannels);
    expect(state.controls).toEqual(controls);
    expect(state.extraChannels).toEqual(extraChannels);
  });
});

describe("processMessage", () => {
  function baseState(): MachineState {
    return createInitialState("m1", "Test");
  }

  describe("temperature messages", () => {
    function monitoringState(): MachineState {
      return { ...baseState(), sessionState: "monitoring" };
    }

    it("adds temperature to history when monitoring", () => {
      const msg: ServerMessage = {
        type: "temperature",
        timestamp_ms: 1000,
        et: 210.5,
        bt: 185.3,
        et_ror: 8.2,
        bt_ror: 12.4,
        extra_channels: {},
      };

      const result = processMessage(monitoringState(), msg);
      expect(result.currentTemp).toEqual({
        timestamp_ms: 1000,
        et: 210.5,
        bt: 185.3,
        et_ror: 8.2,
        bt_ror: 12.4,
      });
      expect(result.history).toHaveLength(1);
    });

    it("does not add to history when idle", () => {
      const result = processMessage(baseState(), {
        type: "temperature",
        timestamp_ms: 1000,
        et: 210,
        bt: 185,
        et_ror: 0,
        bt_ror: 0,
        extra_channels: {},
      });
      expect(result.currentTemp).toBeTruthy();
      expect(result.history).toHaveLength(0);
    });

    it("does not add to history when finished", () => {
      const state = { ...baseState(), sessionState: "finished" as const };
      const result = processMessage(state, {
        type: "temperature",
        timestamp_ms: 1000,
        et: 210,
        bt: 185,
        et_ror: 0,
        bt_ror: 0,
        extra_channels: {},
      });
      expect(result.currentTemp).toBeTruthy();
      expect(result.history).toHaveLength(0);
    });

    it("adds to history when recording", () => {
      const state = { ...baseState(), sessionState: "recording" as const };
      const result = processMessage(state, {
        type: "temperature",
        timestamp_ms: 1000,
        et: 210,
        bt: 185,
        et_ror: 0,
        bt_ror: 0,
        extra_channels: {},
      });
      expect(result.history).toHaveLength(1);
    });

    it("appends multiple temperature readings when monitoring", () => {
      let state = monitoringState();
      for (let i = 0; i < 5; i++) {
        state = processMessage(state, {
          type: "temperature",
          timestamp_ms: i * 1000,
          et: 200 + i,
          bt: 180 + i,
          et_ror: 5,
          bt_ror: 10,
          extra_channels: {},
        });
      }
      expect(state.history).toHaveLength(5);
      expect(state.currentTemp?.et).toBe(204);
    });

    it("clears error on new temperature", () => {
      const state = { ...baseState(), error: "some error" };
      const result = processMessage(state, {
        type: "temperature",
        timestamp_ms: 1000,
        et: 210,
        bt: 185,
        et_ror: 0,
        bt_ror: 0,
        extra_channels: {},
      });
      expect(result.error).toBeNull();
    });

    it("captures extra channels when monitoring", () => {
      const result = processMessage(monitoringState(), {
        type: "temperature",
        timestamp_ms: 1000,
        et: 210,
        bt: 185,
        et_ror: 0,
        bt_ror: 0,
        extra_channels: { Inlet: 250, Exhaust: 180 },
      });
      expect(result.currentExtraChannels).toEqual({ Inlet: 250, Exhaust: 180 });
      expect(result.extraChannelHistory).toHaveLength(1);
      expect(result.extraChannelHistory[0].values).toEqual({
        Inlet: 250,
        Exhaust: 180,
      });
    });

    it("does not add extra channels to history when idle", () => {
      const result = processMessage(baseState(), {
        type: "temperature",
        timestamp_ms: 1000,
        et: 210,
        bt: 185,
        et_ror: 0,
        bt_ror: 0,
        extra_channels: { Inlet: 250 },
      });
      expect(result.currentExtraChannels).toEqual({ Inlet: 250 });
      expect(result.extraChannelHistory).toHaveLength(0);
    });

    it("does not add to extraChannelHistory when no extra channels", () => {
      const result = processMessage(monitoringState(), {
        type: "temperature",
        timestamp_ms: 1000,
        et: 210,
        bt: 185,
        et_ror: 0,
        bt_ror: 0,
        extra_channels: {},
      });
      expect(result.extraChannelHistory).toHaveLength(0);
    });

    it("updates currentControls when readback value changes", () => {
      const controls = [
        {
          name: "Burner",
          channel: "burner",
          min: 0,
          max: 100,
          step: 5,
          unit: "%",
        },
      ];
      let state: MachineState = {
        ...createInitialState("m1", "Test", controls),
        sessionState: "monitoring",
      };
      state = processMessage(state, {
        type: "temperature",
        timestamp_ms: 1000,
        et: 210,
        bt: 185,
        et_ror: 0,
        bt_ror: 0,
        extra_channels: { Burner: 75 },
      });
      expect(state.currentControls).toBeTruthy();
      expect(state.currentControls!.values.burner).toBe(75);
      expect(state.currentControls!.timestamp_ms).toBe(1000);
    });

    it("does not update currentControls when readback is unchanged", () => {
      const controls = [
        {
          name: "Burner",
          channel: "burner",
          min: 0,
          max: 100,
          step: 5,
          unit: "%",
        },
      ];
      let state: MachineState = {
        ...createInitialState("m1", "Test", controls),
        sessionState: "monitoring",
        currentExtraChannels: { Burner: 75 },
      };
      state = processMessage(state, {
        type: "temperature",
        timestamp_ms: 2000,
        et: 210,
        bt: 185,
        et_ror: 0,
        bt_ror: 0,
        extra_channels: { Burner: 75 },
      });
      // currentControls should remain null since value didn't change
      expect(state.currentControls).toBeNull();
    });

    it("records readback changes to controlHistory during recording", () => {
      const controls = [
        {
          name: "Burner",
          channel: "burner",
          min: 0,
          max: 100,
          step: 5,
          unit: "%",
        },
      ];
      let state: MachineState = {
        ...createInitialState("m1", "Test", controls),
        sessionState: "recording",
        currentExtraChannels: { Burner: 50 },
      };
      state = processMessage(state, {
        type: "temperature",
        timestamp_ms: 3000,
        et: 210,
        bt: 185,
        et_ror: 0,
        bt_ror: 0,
        extra_channels: { Burner: 60 },
      });
      expect(state.controlHistory).toHaveLength(1);
      expect(state.controlHistory[0].timestamp_ms).toBe(3000);
      expect(state.controlHistory[0].values.burner).toBe(60);
    });

    it("rounds readback control timestamps to nearest second", () => {
      const controls = [
        {
          name: "Burner",
          channel: "burner",
          min: 0,
          max: 100,
          step: 5,
          unit: "%",
        },
      ];
      let state: MachineState = {
        ...createInitialState("m1", "Test", controls),
        sessionState: "recording",
      };
      state = processMessage(state, {
        type: "temperature",
        timestamp_ms: 3456,
        et: 210,
        bt: 185,
        et_ror: 0,
        bt_ror: 0,
        extra_channels: { Burner: 70 },
      });
      expect(state.currentControls!.timestamp_ms).toBe(3000);
      expect(state.controlHistory[0].timestamp_ms).toBe(3000);
    });

    it("does not record readback to controlHistory during monitoring", () => {
      const controls = [
        {
          name: "Burner",
          channel: "burner",
          min: 0,
          max: 100,
          step: 5,
          unit: "%",
        },
      ];
      let state: MachineState = {
        ...createInitialState("m1", "Test", controls),
        sessionState: "monitoring",
        currentExtraChannels: { Burner: 50 },
      };
      state = processMessage(state, {
        type: "temperature",
        timestamp_ms: 3000,
        et: 210,
        bt: 185,
        et_ror: 0,
        bt_ror: 0,
        extra_channels: { Burner: 60 },
      });
      // currentControls updated, but not controlHistory
      expect(state.currentControls!.values.burner).toBe(60);
      expect(state.controlHistory).toHaveLength(0);
    });

    it("ignores extra channels not matching control configs", () => {
      const controls = [
        {
          name: "Burner",
          channel: "burner",
          min: 0,
          max: 100,
          step: 5,
          unit: "%",
        },
      ];
      let state: MachineState = {
        ...createInitialState("m1", "Test", controls),
        sessionState: "monitoring",
      };
      state = processMessage(state, {
        type: "temperature",
        timestamp_ms: 1000,
        et: 210,
        bt: 185,
        et_ror: 0,
        bt_ror: 0,
        extra_channels: { Inlet: 250 },
      });
      // "Inlet" doesn't match any control name, so no control update
      expect(state.currentControls).toBeNull();
    });
  });

  describe("event messages", () => {
    it("adds event to events list", () => {
      const result = processMessage(baseState(), {
        type: "event",
        event_type: "CHARGE",
        timestamp_ms: 5000,
        auto_detected: true,
        bt_at_event: 155.0,
        et_at_event: 210.0,
      });
      expect(result.events).toHaveLength(1);
      expect(result.events[0].event_type).toBe("CHARGE");
      expect(result.events[0].auto_detected).toBe(true);
    });

    it("appends multiple events", () => {
      let state = baseState();
      state = processMessage(state, {
        type: "event",
        event_type: "CHARGE",
        timestamp_ms: 5000,
        auto_detected: false,
        bt_at_event: 155,
        et_at_event: 210,
      });
      state = processMessage(state, {
        type: "event",
        event_type: "FCs",
        timestamp_ms: 300000,
        auto_detected: false,
        bt_at_event: 200,
        et_at_event: 230,
      });
      expect(state.events).toHaveLength(2);
      expect(state.events[1].event_type).toBe("FCs");
    });
  });

  describe("state messages", () => {
    it("updates session state", () => {
      const result = processMessage(baseState(), {
        type: "state",
        state: "monitoring",
        previous_state: "idle",
      });
      expect(result.sessionState).toBe("monitoring");
    });

    it("clears history and currentTemp when monitoring starts", () => {
      let state: MachineState = { ...baseState(), sessionState: "monitoring" };
      state = processMessage(state, {
        type: "temperature",
        timestamp_ms: 1000,
        et: 200,
        bt: 180,
        et_ror: 0,
        bt_ror: 0,
        extra_channels: {},
      });
      expect(state.history).toHaveLength(1);
      expect(state.currentTemp).toBeTruthy();
      // Stop monitoring → idle, then start again
      state = processMessage(state, {
        type: "state",
        state: "idle",
        previous_state: "monitoring",
      });
      state = processMessage(state, {
        type: "state",
        state: "monitoring",
        previous_state: "idle",
      });
      expect(state.history).toEqual([]);
      expect(state.controlHistory).toEqual([]);
      expect(state.extraChannelHistory).toEqual([]);
      expect(state.events).toEqual([]);
      expect(state.currentTemp).toBeNull();
    });

    it("keeps last 5s of history rebased to negative timestamps when recording starts", () => {
      let state: MachineState = { ...baseState(), sessionState: "monitoring" };
      // Add data during monitoring
      for (const ts of [1000, 3000, 8000]) {
        state = processMessage(state, {
          type: "temperature",
          timestamp_ms: ts,
          et: 200,
          bt: 180,
          et_ror: 0,
          bt_ror: 0,
          extra_channels: { Inlet: 250 },
        });
        state = recordControlChange(state, "burner", 80, ts);
      }
      state = processMessage(state, {
        type: "event",
        event_type: "CHARGE",
        timestamp_ms: 5000,
        auto_detected: false,
        bt_at_event: 180,
        et_at_event: 200,
      });
      expect(state.history).toHaveLength(3);
      expect(state.events).toHaveLength(1);

      state = processMessage(state, {
        type: "state",
        state: "recording",
        previous_state: "monitoring",
      });
      // Only points at 3000 and 8000 kept (cutoff = 8000 - 5000 = 3000)
      // Rebased by lastTs 8000: 3000→-5000, 8000→0
      // The last monitoring point lands at 0, tail is negative.
      // Backend resets its clock so new data arrives starting from ~0.
      expect(state.history).toHaveLength(2);
      expect(state.history[0].timestamp_ms).toBe(-5000);
      expect(state.history[1].timestamp_ms).toBe(0);
      expect(state.events).toEqual([]);
      // Control history is replaced with a t=0 snapshot of currentControls
      expect(state.controlHistory).toHaveLength(1);
      expect(state.controlHistory[0].timestamp_ms).toBe(0);
      expect(state.controlHistory[0].values.burner).toBe(80);
      expect(state.extraChannelHistory).toHaveLength(2);
      expect(state.extraChannelHistory[0].timestamp_ms).toBe(-5000);
    });

    it("rebases currentTemp timestamp when recording starts", () => {
      let state: MachineState = { ...baseState(), sessionState: "monitoring" };
      // Simulate monitoring for 60 seconds
      for (const ts of [55000, 58000, 60000]) {
        state = processMessage(state, {
          type: "temperature",
          timestamp_ms: ts,
          et: 200,
          bt: 180,
          et_ror: 0,
          bt_ror: 0,
          extra_channels: {},
        });
      }
      expect(state.currentTemp!.timestamp_ms).toBe(60000);

      state = processMessage(state, {
        type: "state",
        state: "recording",
        previous_state: "monitoring",
      });
      // currentTemp should be rebased: 60000 - 60000 = 0
      expect(state.currentTemp).not.toBeNull();
      expect(state.currentTemp!.timestamp_ms).toBe(0);
    });

    it("sets currentTemp to null when recording starts with no data", () => {
      let state = baseState();
      state = processMessage(state, {
        type: "state",
        state: "recording",
        previous_state: "monitoring",
      });
      expect(state.currentTemp).toBeNull();
    });

    it("clears all history when recording starts with no data", () => {
      let state = baseState();
      state = processMessage(state, {
        type: "state",
        state: "recording",
        previous_state: "monitoring",
      });
      expect(state.history).toEqual([]);
      expect(state.events).toEqual([]);
      expect(state.controlHistory).toEqual([]);
      expect(state.extraChannelHistory).toEqual([]);
    });

    it("preserves history for non-recording state changes", () => {
      let state: MachineState = { ...baseState(), sessionState: "monitoring" };
      state = processMessage(state, {
        type: "temperature",
        timestamp_ms: 1000,
        et: 200,
        bt: 180,
        et_ror: 0,
        bt_ror: 0,
        extra_channels: {},
      });
      state = processMessage(state, {
        type: "state",
        state: "finished",
        previous_state: "recording",
      });
      expect(state.history).toHaveLength(1);
    });

    it("transitions to idle on stop_monitoring", () => {
      const state = { ...baseState(), sessionState: "monitoring" as const };
      const result = processMessage(state, {
        type: "state",
        state: "idle",
        previous_state: "monitoring",
      });
      expect(result.sessionState).toBe("idle");
    });
  });

  describe("connection messages", () => {
    it("updates driver state", () => {
      const result = processMessage(baseState(), {
        type: "connection",
        driver_state: "connected",
        driver_name: "Test Driver",
        message: "Connected",
      });
      expect(result.driverState).toBe("connected");
    });
  });

  describe("error messages", () => {
    it("sets error message", () => {
      const result = processMessage(baseState(), {
        type: "error",
        code: "DRIVER_READ_FAILED",
        message: "Connection timeout",
        recoverable: true,
      });
      expect(result.error).toBe("Connection timeout");
    });
  });

  describe("passthrough messages", () => {
    it("returns state unchanged for alarm", () => {
      const state = baseState();
      const result = processMessage(state, {
        type: "alarm",
        alarm_id: "a1",
        severity: "warning",
        message: "test",
        timestamp_ms: 0,
        bt: 180,
        et: 210,
      });
      expect(result).toBe(state);
    });

    it("control_ack is a no-op (does not update state)", () => {
      const state = baseState();
      const result = processMessage(state, {
        type: "control_ack",
        channel: "burner",
        value: 50,
        applied: true,
        enabled: true,
        message: "ok",
      });
      expect(result).toBe(state);
    });

    it("snapshots readback values at t=0 when recording starts", () => {
      const controls = [
        {
          name: "Burner",
          channel: "burner",
          min: 0,
          max: 100,
          step: 5,
          unit: "%",
        },
        {
          name: "Airflow",
          channel: "airflow",
          min: 0,
          max: 100,
          step: 5,
          unit: "%",
        },
      ];
      let state: MachineState = {
        ...createInitialState("m1", "Test", controls),
        sessionState: "monitoring",
      };
      // Simulate readback values arriving during monitoring
      state = processMessage(state, {
        type: "temperature",
        timestamp_ms: 1000,
        et: 200,
        bt: 180,
        et_ror: 0,
        bt_ror: 0,
        extra_channels: { Burner: 80, Airflow: 50 },
      });
      // Start recording
      state = processMessage(state, {
        type: "state",
        state: "recording",
        previous_state: "monitoring",
      });
      // Should have a single snapshot at t=0 with readback-sourced values
      expect(state.controlHistory).toHaveLength(1);
      expect(state.controlHistory[0].timestamp_ms).toBe(0);
      expect(state.controlHistory[0].values.burner).toBe(80);
      expect(state.controlHistory[0].values.airflow).toBe(50);
    });

    it("t=0 snapshot overlays slider values on top of readback", () => {
      const controls = [
        {
          name: "Burner",
          channel: "burner",
          min: 0,
          max: 100,
          step: 5,
          unit: "%",
        },
      ];
      let state: MachineState = {
        ...createInitialState("m1", "Test", controls),
        sessionState: "monitoring",
      };
      // Readback arrives
      state = processMessage(state, {
        type: "temperature",
        timestamp_ms: 1000,
        et: 200,
        bt: 180,
        et_ror: 0,
        bt_ror: 0,
        extra_channels: { Burner: 60 },
      });
      // User manually sets slider to different value
      state = processControlInput(state, "burner", 75);
      // Start recording — slider value (75) should win over readback (60)
      state = processMessage(state, {
        type: "state",
        state: "recording",
        previous_state: "monitoring",
      });
      expect(state.controlHistory).toHaveLength(1);
      expect(state.controlHistory[0].values.burner).toBe(75);
    });

    it("returns state unchanged for replay", () => {
      const state = baseState();
      const result = processMessage(state, {
        type: "replay",
        timestamp_ms: 0,
        et: 200,
        bt: 180,
        et_ror: 0,
        bt_ror: 0,
        controls: {},
        progress_pct: 0,
        total_duration_ms: 600000,
      });
      expect(result).toBe(state);
    });
  });
});

describe("recordControlChange", () => {
  function baseState(): MachineState {
    return createInitialState("m1", "Test");
  }

  it("appends control point to history", () => {
    const state = recordControlChange(baseState(), "burner", 75, 5000);
    expect(state.controlHistory).toHaveLength(1);
    expect(state.controlHistory[0].values.burner).toBe(75);
    expect(state.controlHistory[0].timestamp_ms).toBe(5000);
  });

  it("updates currentControls", () => {
    const state = recordControlChange(baseState(), "airflow", 60, 3000);
    expect(state.currentControls).toBeTruthy();
    expect(state.currentControls!.values.airflow).toBe(60);
  });

  it("preserves other channels from previous controls", () => {
    let state = recordControlChange(baseState(), "burner", 80, 1000);
    state = recordControlChange(state, "airflow", 50, 2000);
    expect(state.currentControls!.values.burner).toBe(80);
    expect(state.currentControls!.values.airflow).toBe(50);
    expect(state.controlHistory).toHaveLength(2);
  });

  it("starts with empty values when no previous controls", () => {
    const state = recordControlChange(baseState(), "drum", 90, 1000);
    expect(state.currentControls!.values.drum).toBe(90);
    expect(state.currentControls!.values.burner).toBeUndefined();
  });
});

describe("processControlInput", () => {
  function baseState(): MachineState {
    return createInitialState("m1", "Test");
  }

  it("updates currentControls with native value", () => {
    const state = processControlInput(baseState(), "burner", 75);
    expect(state.currentControls).toBeTruthy();
    expect(state.currentControls!.values.burner).toBe(75);
  });

  it("records to controlHistory during recording", () => {
    const state: MachineState = {
      ...baseState(),
      sessionState: "recording",
      currentTemp: {
        timestamp_ms: 5000,
        et: 200,
        bt: 180,
        et_ror: 0,
        bt_ror: 0,
      },
    };
    const result = processControlInput(state, "burner", 80);
    expect(result.controlHistory).toHaveLength(1);
    expect(result.controlHistory[0].timestamp_ms).toBe(5000);
    expect(result.controlHistory[0].values.burner).toBe(80);
  });

  it("does not record to controlHistory outside recording", () => {
    const state: MachineState = {
      ...baseState(),
      sessionState: "monitoring",
      currentTemp: {
        timestamp_ms: 5000,
        et: 200,
        bt: 180,
        et_ror: 0,
        bt_ror: 0,
      },
    };
    const result = processControlInput(state, "burner", 80);
    expect(result.currentControls!.values.burner).toBe(80);
    expect(result.controlHistory).toHaveLength(0);
  });

  it("preserves other channels in currentControls", () => {
    let state: MachineState = {
      ...baseState(),
      sessionState: "recording",
      currentTemp: {
        timestamp_ms: 3000,
        et: 200,
        bt: 180,
        et_ror: 0,
        bt_ror: 0,
      },
    };
    state = processControlInput(state, "burner", 80);
    state = processControlInput(state, "airflow", 60);
    expect(state.currentControls!.values.burner).toBe(80);
    expect(state.currentControls!.values.airflow).toBe(60);
    expect(state.controlHistory).toHaveLength(2);
  });

  it("uses timestamp 0 when no current temperature", () => {
    const state: MachineState = {
      ...baseState(),
      sessionState: "recording",
    };
    const result = processControlInput(state, "burner", 50);
    expect(result.controlHistory[0].timestamp_ms).toBe(0);
  });

  it("rounds slider control timestamps to nearest second", () => {
    const state: MachineState = {
      ...baseState(),
      sessionState: "recording",
      currentTemp: {
        timestamp_ms: 4700,
        et: 200,
        bt: 180,
        et_ror: 0,
        bt_ror: 0,
      },
    };
    const result = processControlInput(state, "burner", 80);
    expect(result.currentControls!.timestamp_ms).toBe(5000);
    expect(result.controlHistory[0].timestamp_ms).toBe(5000);
  });

  it("records individual channel per history entry", () => {
    let state: MachineState = {
      ...baseState(),
      sessionState: "recording",
      currentTemp: {
        timestamp_ms: 2000,
        et: 200,
        bt: 180,
        et_ror: 0,
        bt_ror: 0,
      },
    };
    state = processControlInput(state, "burner", 70);
    state = processControlInput(state, "airflow", 40);
    // Each entry should only have the channel that was changed
    expect(state.controlHistory[0].values).toEqual({ burner: 70 });
    expect(state.controlHistory[1].values).toEqual({ airflow: 40 });
  });
});

describe("formatTime", () => {
  it("formats zero", () => {
    expect(formatTime(0)).toBe("0:00");
  });

  it("formats seconds only", () => {
    expect(formatTime(45000)).toBe("0:45");
  });

  it("formats minutes and seconds", () => {
    expect(formatTime(125000)).toBe("2:05");
  });

  it("formats exact minutes", () => {
    expect(formatTime(300000)).toBe("5:00");
  });

  it("pads single-digit seconds", () => {
    expect(formatTime(63000)).toBe("1:03");
  });

  it("handles large values", () => {
    expect(formatTime(900000)).toBe("15:00");
  });
});
