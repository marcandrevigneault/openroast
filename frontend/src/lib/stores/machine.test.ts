import { describe, it, expect } from "vitest";
import {
  createInitialState,
  processMessage,
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
    it("adds temperature to history and sets currentTemp", () => {
      const msg: ServerMessage = {
        type: "temperature",
        timestamp_ms: 1000,
        et: 210.5,
        bt: 185.3,
        et_ror: 8.2,
        bt_ror: 12.4,
        extra_channels: {},
      };

      const result = processMessage(baseState(), msg);
      expect(result.currentTemp).toEqual({
        timestamp_ms: 1000,
        et: 210.5,
        bt: 185.3,
        et_ror: 8.2,
        bt_ror: 12.4,
      });
      expect(result.history).toHaveLength(1);
    });

    it("appends multiple temperature readings", () => {
      let state = baseState();
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

    it("captures extra channels from temperature message", () => {
      const result = processMessage(baseState(), {
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

    it("does not add to extraChannelHistory when no extra channels", () => {
      const result = processMessage(baseState(), {
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

    it("clears history, events, controlHistory, and extraChannelHistory when recording starts", () => {
      let state = baseState();
      state = processMessage(state, {
        type: "temperature",
        timestamp_ms: 1000,
        et: 200,
        bt: 180,
        et_ror: 0,
        bt_ror: 0,
        extra_channels: { Inlet: 250 },
      });
      state = processMessage(state, {
        type: "event",
        event_type: "CHARGE",
        timestamp_ms: 1000,
        auto_detected: false,
        bt_at_event: 180,
        et_at_event: 200,
      });
      state = recordControlChange(state, "burner", 80, 1000);
      expect(state.history).toHaveLength(1);
      expect(state.events).toHaveLength(1);
      expect(state.controlHistory).toHaveLength(1);
      expect(state.extraChannelHistory).toHaveLength(1);

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
      let state = baseState();
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

    it("updates currentControls on control_ack", () => {
      const state = baseState();
      const result = processMessage(state, {
        type: "control_ack",
        channel: "burner",
        value: 50,
        applied: true,
        message: "ok",
      });
      expect(result.currentControls).toBeTruthy();
      expect(result.currentControls!.values.burner).toBe(50);
    });

    it("preserves other channels on control_ack", () => {
      let state = baseState();
      state = processMessage(state, {
        type: "control_ack",
        channel: "burner",
        value: 80,
        applied: true,
        message: "ok",
      });
      state = processMessage(state, {
        type: "control_ack",
        channel: "airflow",
        value: 60,
        applied: true,
        message: "ok",
      });
      expect(state.currentControls!.values.burner).toBe(80);
      expect(state.currentControls!.values.airflow).toBe(60);
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
