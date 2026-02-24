import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  playAlarmSound,
  stopAlarmSound,
  stopAllAlarmSounds,
  isPlaying,
  _resetForTesting,
} from "./alarm-audio";

// Minimal AudioContext mock as a class (required for `new AudioContext()`)
class MockAudioContext {
  state = "running";
  currentTime = 0;
  destination = {};
  resume = vi.fn();

  createOscillator() {
    return {
      type: "sine" as OscillatorType,
      frequency: {
        value: 0,
        setValueAtTime: vi.fn(),
        linearRampToValueAtTime: vi.fn(),
      },
      connect: vi.fn(),
      disconnect: vi.fn(),
      start: vi.fn(),
      stop: vi.fn(),
      onended: null as (() => void) | null,
    };
  }

  createGain() {
    return {
      gain: {
        value: 0,
        setValueAtTime: vi.fn(),
        linearRampToValueAtTime: vi.fn(),
      },
      connect: vi.fn(),
      disconnect: vi.fn(),
    };
  }
}

beforeEach(() => {
  _resetForTesting();
  vi.stubGlobal("AudioContext", MockAudioContext);
});

afterEach(() => {
  _resetForTesting();
  vi.unstubAllGlobals();
});

describe("playAlarmSound", () => {
  it("returns a unique playback ID", () => {
    const id1 = playAlarmSound("beep", "once");
    const id2 = playAlarmSound("chime", "once");
    expect(id1).toBeTruthy();
    expect(id2).toBeTruthy();
    expect(id1).not.toBe(id2);
  });

  it("returns empty string when AudioContext unavailable", () => {
    _resetForTesting();
    vi.stubGlobal("AudioContext", undefined);
    const id = playAlarmSound("beep", "once");
    expect(id).toBe("");
  });

  it("tracks playback as active", () => {
    const id = playAlarmSound("beep", "once");
    expect(isPlaying(id)).toBe(true);
  });
});

describe("stopAlarmSound", () => {
  it("stops and removes active playback", () => {
    const id = playAlarmSound("buzz", "3x");
    expect(isPlaying(id)).toBe(true);
    stopAlarmSound(id);
    expect(isPlaying(id)).toBe(false);
  });

  it("does not throw for unknown ID", () => {
    expect(() => stopAlarmSound("nonexistent")).not.toThrow();
  });
});

describe("stopAllAlarmSounds", () => {
  it("clears all active sounds", () => {
    const id1 = playAlarmSound("beep", "3x");
    const id2 = playAlarmSound("siren", "3x");
    expect(isPlaying(id1)).toBe(true);
    expect(isPlaying(id2)).toBe(true);
    stopAllAlarmSounds();
    expect(isPlaying(id1)).toBe(false);
    expect(isPlaying(id2)).toBe(false);
  });
});

describe("isPlaying", () => {
  it("returns false for unknown ID", () => {
    expect(isPlaying("nonexistent")).toBe(false);
  });

  it("returns false after sound is stopped", () => {
    const id = playAlarmSound("chime", "once");
    stopAlarmSound(id);
    expect(isPlaying(id)).toBe(false);
  });
});
