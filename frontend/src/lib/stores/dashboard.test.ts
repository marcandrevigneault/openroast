import { describe, it, expect } from "vitest";
import {
  createDashboardState,
  addMachine,
  removeMachine,
  updateLayout,
  generateMachineId,
  type DashboardState,
  type DashboardMachine,
} from "./dashboard";

describe("createDashboardState", () => {
  it("creates empty state with default layout", () => {
    const state = createDashboardState();
    expect(state.machines).toEqual([]);
    expect(state.layout.mode).toBe("grid");
    expect(state.layout.columns).toBe(2);
  });
});

describe("addMachine", () => {
  it("adds a machine", () => {
    const state = createDashboardState();
    const result = addMachine(state, { id: "m1", name: "Roaster 1" });
    expect(result.machines).toHaveLength(1);
    expect(result.machines[0].id).toBe("m1");
    expect(result.machines[0].name).toBe("Roaster 1");
  });

  it("appends to existing machines", () => {
    let state = createDashboardState();
    state = addMachine(state, { id: "m1", name: "Roaster 1" });
    state = addMachine(state, { id: "m2", name: "Roaster 2" });
    expect(state.machines).toHaveLength(2);
  });

  it("deduplicates by id", () => {
    let state = createDashboardState();
    state = addMachine(state, { id: "m1", name: "Roaster 1" });
    state = addMachine(state, { id: "m1", name: "Duplicate" });
    expect(state.machines).toHaveLength(1);
    expect(state.machines[0].name).toBe("Roaster 1");
  });

  it("does not mutate original state", () => {
    const state = createDashboardState();
    const result = addMachine(state, { id: "m1", name: "Roaster 1" });
    expect(state.machines).toHaveLength(0);
    expect(result.machines).toHaveLength(1);
  });
});

describe("removeMachine", () => {
  it("removes by id", () => {
    let state = createDashboardState();
    state = addMachine(state, { id: "m1", name: "Roaster 1" });
    state = addMachine(state, { id: "m2", name: "Roaster 2" });
    state = removeMachine(state, "m1");
    expect(state.machines).toHaveLength(1);
    expect(state.machines[0].id).toBe("m2");
  });

  it("no-op when id not found", () => {
    let state = createDashboardState();
    state = addMachine(state, { id: "m1", name: "Roaster 1" });
    state = removeMachine(state, "nonexistent");
    expect(state.machines).toHaveLength(1);
  });
});

describe("updateLayout", () => {
  it("updates mode", () => {
    const state = createDashboardState();
    const result = updateLayout(state, { mode: "vertical" });
    expect(result.layout.mode).toBe("vertical");
    expect(result.layout.columns).toBe(2); // preserved
  });

  it("updates columns", () => {
    const state = createDashboardState();
    const result = updateLayout(state, { columns: 3 });
    expect(result.layout.columns).toBe(3);
    expect(result.layout.mode).toBe("grid"); // preserved
  });

  it("updates both", () => {
    const state = createDashboardState();
    const result = updateLayout(state, { mode: "horizontal", columns: 4 });
    expect(result.layout.mode).toBe("horizontal");
    expect(result.layout.columns).toBe(4);
  });
});

describe("generateMachineId", () => {
  it("returns unique ids", () => {
    const a = generateMachineId();
    const b = generateMachineId();
    expect(a).not.toBe(b);
  });

  it("returns string starting with machine-", () => {
    const id = generateMachineId();
    expect(id).toMatch(/^machine-\d+$/);
  });
});
