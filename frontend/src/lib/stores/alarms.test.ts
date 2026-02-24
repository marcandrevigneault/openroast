import { describe, it, expect } from "vitest";
import {
  createAlarmSet,
  addAlarm,
  removeAlarm,
  toggleAlarm,
  resetAlarms,
  resolveSensorValues,
  evaluateAlarms,
  formatSensor,
  formatAlarm,
  type AlarmDef,
  type AlarmSet,
  type AlarmSensor,
} from "./alarms";

function makeAlarm(overrides: Partial<AlarmDef> = {}): AlarmDef {
  return {
    id: "a1",
    sensor: { type: "bt" },
    threshold: 200,
    direction: "rising",
    sound: "beep",
    repeat: "once",
    enabled: true,
    fired: false,
    playbackId: null,
    ...overrides,
  };
}

function makeSet(
  alarms: AlarmDef[] = [],
  status: AlarmSet["status"] = "idle",
): AlarmSet {
  return { alarms, status };
}

// Default sensor values for evaluation
const DEFAULTS = {
  currentEt: 220,
  currentBt: 200,
  currentEtRor: 8,
  currentBtRor: 12,
  currentExtras: { Inlet: 150 } as Record<string, number>,
  previousEt: 210,
  previousBt: 190,
  previousEtRor: 7,
  previousBtRor: 11,
  previousExtras: { Inlet: 140 } as Record<string, number>,
};

describe("createAlarmSet", () => {
  it("returns empty set with idle status", () => {
    const set = createAlarmSet();
    expect(set.alarms).toEqual([]);
    expect(set.status).toBe("idle");
  });
});

describe("addAlarm", () => {
  it("adds alarm with generated id", () => {
    const set = addAlarm(createAlarmSet(), {
      sensor: { type: "bt" },
      threshold: 200,
      direction: "rising",
      sound: "beep",
      repeat: "once",
      enabled: true,
    });
    expect(set.alarms).toHaveLength(1);
    expect(set.alarms[0].id).toBeTruthy();
    expect(set.alarms[0].fired).toBe(false);
    expect(set.alarms[0].playbackId).toBeNull();
  });

  it("generates unique IDs", () => {
    let set = createAlarmSet();
    set = addAlarm(set, {
      sensor: { type: "bt" },
      threshold: 200,
      direction: "rising",
      sound: "beep",
      repeat: "once",
      enabled: true,
    });
    set = addAlarm(set, {
      sensor: { type: "et" },
      threshold: 300,
      direction: "falling",
      sound: "chime",
      repeat: "3x",
      enabled: true,
    });
    expect(set.alarms[0].id).not.toBe(set.alarms[1].id);
  });
});

describe("removeAlarm", () => {
  it("removes alarm by id", () => {
    const set = makeSet([makeAlarm({ id: "a1" }), makeAlarm({ id: "a2" })]);
    const result = removeAlarm(set, "a1");
    expect(result.alarms).toHaveLength(1);
    expect(result.alarms[0].id).toBe("a2");
  });

  it("returns unchanged set for unknown id", () => {
    const set = makeSet([makeAlarm({ id: "a1" })]);
    const result = removeAlarm(set, "unknown");
    expect(result.alarms).toHaveLength(1);
  });
});

describe("toggleAlarm", () => {
  it("flips enabled flag", () => {
    const set = makeSet([makeAlarm({ id: "a1", enabled: true })]);
    const result = toggleAlarm(set, "a1");
    expect(result.alarms[0].enabled).toBe(false);
    const again = toggleAlarm(result, "a1");
    expect(again.alarms[0].enabled).toBe(true);
  });
});

describe("resetAlarms", () => {
  it("clears fired and playbackId, sets status to idle", () => {
    const set = makeSet(
      [
        makeAlarm({ id: "a1", fired: true, playbackId: "pb-1" }),
        makeAlarm({ id: "a2", fired: true, playbackId: "pb-2" }),
      ],
      "completed",
    );
    const result = resetAlarms(set);
    expect(result.status).toBe("idle");
    expect(result.alarms[0].fired).toBe(false);
    expect(result.alarms[0].playbackId).toBeNull();
    expect(result.alarms[1].fired).toBe(false);
    expect(result.alarms[1].playbackId).toBeNull();
  });
});

describe("resolveSensorValues", () => {
  const args = [
    DEFAULTS.currentEt,
    DEFAULTS.currentBt,
    DEFAULTS.currentEtRor,
    DEFAULTS.currentBtRor,
    DEFAULTS.currentExtras,
    DEFAULTS.previousEt,
    DEFAULTS.previousBt,
    DEFAULTS.previousEtRor,
    DEFAULTS.previousBtRor,
    DEFAULTS.previousExtras,
  ] as const;

  it("resolves ET sensor", () => {
    const r = resolveSensorValues({ type: "et" }, ...args);
    expect(r).toEqual({ current: 220, previous: 210 });
  });

  it("resolves BT sensor", () => {
    const r = resolveSensorValues({ type: "bt" }, ...args);
    expect(r).toEqual({ current: 200, previous: 190 });
  });

  it("resolves ET RoR sensor", () => {
    const r = resolveSensorValues({ type: "et_ror" }, ...args);
    expect(r).toEqual({ current: 8, previous: 7 });
  });

  it("resolves BT RoR sensor", () => {
    const r = resolveSensorValues({ type: "bt_ror" }, ...args);
    expect(r).toEqual({ current: 12, previous: 11 });
  });

  it("resolves extra channel sensor", () => {
    const r = resolveSensorValues(
      { type: "extra", channelName: "Inlet" },
      ...args,
    );
    expect(r).toEqual({ current: 150, previous: 140 });
  });

  it("returns null for missing extra channel", () => {
    const r = resolveSensorValues(
      { type: "extra", channelName: "Missing" },
      ...args,
    );
    expect(r).toBeNull();
  });
});

describe("evaluateAlarms", () => {
  function evaluate(set: AlarmSet, overrides: Partial<typeof DEFAULTS> = {}) {
    const d = { ...DEFAULTS, ...overrides };
    return evaluateAlarms(
      set,
      d.currentEt,
      d.currentBt,
      d.currentEtRor,
      d.currentBtRor,
      d.currentExtras,
      d.previousEt,
      d.previousBt,
      d.previousEtRor,
      d.previousBtRor,
      d.previousExtras,
    );
  }

  it("does nothing when status is idle", () => {
    const set = makeSet([makeAlarm()], "idle");
    const { triggered } = evaluate(set);
    expect(triggered).toHaveLength(0);
  });

  it("fires rising alarm on threshold crossing", () => {
    // BT: prev=190, curr=200, threshold=195 → crossing
    const alarm = makeAlarm({
      sensor: { type: "bt" },
      threshold: 195,
      direction: "rising",
    });
    const set = makeSet([alarm], "armed");
    const { set: updated, triggered } = evaluate(set);
    expect(triggered).toHaveLength(1);
    expect(triggered[0].alarmId).toBe("a1");
    expect(updated.alarms[0].fired).toBe(true);
  });

  it("does not fire rising alarm when already above threshold", () => {
    // BT: prev=200, curr=210, threshold=195 → no crossing (both above)
    const alarm = makeAlarm({
      sensor: { type: "bt" },
      threshold: 195,
      direction: "rising",
    });
    const set = makeSet([alarm], "armed");
    const { triggered } = evaluate(set, { previousBt: 200, currentBt: 210 });
    expect(triggered).toHaveLength(0);
  });

  it("fires falling alarm on threshold crossing", () => {
    // ET: prev=220, curr=200, threshold=210 → crossing
    const alarm = makeAlarm({
      sensor: { type: "et" },
      threshold: 210,
      direction: "falling",
    });
    const set = makeSet([alarm], "armed");
    const { triggered } = evaluate(set, { previousEt: 220, currentEt: 200 });
    expect(triggered).toHaveLength(1);
  });

  it("does not fire falling alarm when already below threshold", () => {
    const alarm = makeAlarm({
      sensor: { type: "et" },
      threshold: 250,
      direction: "falling",
    });
    const set = makeSet([alarm], "armed");
    const { triggered } = evaluate(set);
    expect(triggered).toHaveLength(0);
  });

  it("fires both direction alarm on rising crossing", () => {
    const alarm = makeAlarm({
      sensor: { type: "bt" },
      threshold: 195,
      direction: "both",
    });
    const set = makeSet([alarm], "armed");
    const { triggered } = evaluate(set);
    expect(triggered).toHaveLength(1);
  });

  it("fires both direction alarm on falling crossing", () => {
    const alarm = makeAlarm({
      sensor: { type: "bt" },
      threshold: 195,
      direction: "both",
    });
    const set = makeSet([alarm], "armed");
    const { triggered } = evaluate(set, { previousBt: 200, currentBt: 190 });
    expect(triggered).toHaveLength(1);
  });

  it("skips already-fired alarms", () => {
    const alarm = makeAlarm({ fired: true, threshold: 195 });
    const set = makeSet([alarm], "armed");
    const { triggered } = evaluate(set);
    expect(triggered).toHaveLength(0);
  });

  it("skips disabled alarms", () => {
    const alarm = makeAlarm({ enabled: false, threshold: 195 });
    const set = makeSet([alarm], "armed");
    const { triggered } = evaluate(set);
    expect(triggered).toHaveLength(0);
  });

  it("fires multiple alarms in one evaluation", () => {
    const a1 = makeAlarm({
      id: "a1",
      sensor: { type: "bt" },
      threshold: 195,
      direction: "rising",
    });
    const a2 = makeAlarm({
      id: "a2",
      sensor: { type: "et" },
      threshold: 215,
      direction: "rising",
    });
    const set = makeSet([a1, a2], "armed");
    const { triggered } = evaluate(set);
    expect(triggered).toHaveLength(2);
  });

  it("returns completed when all enabled alarms are fired", () => {
    const alarm = makeAlarm({ threshold: 195 });
    const set = makeSet([alarm], "armed");
    const { set: updated } = evaluate(set);
    expect(updated.status).toBe("completed");
  });

  it("stays armed when unfired enabled alarms remain", () => {
    const a1 = makeAlarm({ id: "a1", threshold: 195 }); // will fire
    const a2 = makeAlarm({ id: "a2", threshold: 999 }); // won't fire
    const set = makeSet([a1, a2], "armed");
    const { set: updated } = evaluate(set);
    expect(updated.status).toBe("armed");
  });

  it("evaluates ET RoR sensor", () => {
    // ET RoR: prev=7, curr=8, threshold=7.5 → rising crossing
    const alarm = makeAlarm({
      sensor: { type: "et_ror" },
      threshold: 7.5,
      direction: "rising",
    });
    const set = makeSet([alarm], "armed");
    const { triggered } = evaluate(set);
    expect(triggered).toHaveLength(1);
    expect(triggered[0].sensorLabel).toBe("ET RoR");
  });

  it("evaluates BT RoR sensor", () => {
    // BT RoR: prev=11, curr=12, threshold=11.5 → rising crossing
    const alarm = makeAlarm({
      sensor: { type: "bt_ror" },
      threshold: 11.5,
      direction: "rising",
    });
    const set = makeSet([alarm], "armed");
    const { triggered } = evaluate(set);
    expect(triggered).toHaveLength(1);
    expect(triggered[0].sensorLabel).toBe("BT RoR");
  });

  it("evaluates extra channel sensor", () => {
    // Inlet: prev=140, curr=150, threshold=145 → rising crossing
    const alarm = makeAlarm({
      sensor: { type: "extra", channelName: "Inlet" },
      threshold: 145,
      direction: "rising",
    });
    const set = makeSet([alarm], "armed");
    const { triggered } = evaluate(set);
    expect(triggered).toHaveLength(1);
    expect(triggered[0].sensorLabel).toBe("Inlet");
  });

  it("returns correct trigger result fields", () => {
    const alarm = makeAlarm({
      sensor: { type: "bt" },
      threshold: 195,
      direction: "rising",
      sound: "chime",
      repeat: "3x",
    });
    const set = makeSet([alarm], "armed");
    const { triggered } = evaluate(set);
    expect(triggered[0]).toEqual({
      alarmId: "a1",
      sound: "chime",
      repeat: "3x",
      sensorLabel: "BT",
      threshold: 195,
      direction: "rising",
    });
  });
});

describe("formatSensor", () => {
  const cases: [AlarmSensor, string][] = [
    [{ type: "et" }, "ET"],
    [{ type: "bt" }, "BT"],
    [{ type: "et_ror" }, "ET RoR"],
    [{ type: "bt_ror" }, "BT RoR"],
    [{ type: "extra", channelName: "Inlet" }, "Inlet"],
  ];

  it.each(cases)("formats %j as %s", (sensor, expected) => {
    expect(formatSensor(sensor)).toBe(expected);
  });
});

describe("formatAlarm", () => {
  it("formats rising alarm", () => {
    expect(
      formatAlarm(makeAlarm({ threshold: 200, direction: "rising" })),
    ).toBe("BT >= 200");
  });

  it("formats falling alarm", () => {
    expect(
      formatAlarm(
        makeAlarm({
          threshold: 150,
          direction: "falling",
          sensor: { type: "et" },
        }),
      ),
    ).toBe("ET <= 150");
  });

  it("formats both direction alarm", () => {
    expect(
      formatAlarm(
        makeAlarm({
          threshold: 10,
          direction: "both",
          sensor: { type: "bt_ror" },
        }),
      ),
    ).toBe("BT RoR ↕ 10");
  });
});
