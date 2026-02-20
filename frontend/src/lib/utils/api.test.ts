import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  saveProfile,
  listProfiles,
  getProfile,
  deleteProfile,
  saveSchedule,
  listSchedules,
  getSchedule,
  deleteSchedule,
} from "./api";

const mockFetch = vi.fn();

beforeEach(() => {
  vi.stubGlobal("fetch", mockFetch);
  mockFetch.mockReset();
});

describe("saveProfile", () => {
  it("posts profile and returns id", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: "abc-123" }),
    });

    const result = await saveProfile({
      profile: {
        name: "Test",
        machine: "Stratto",
        temperatures: [],
        events: [],
        controls: {},
      },
    });

    expect(result.id).toBe("abc-123");
    expect(mockFetch).toHaveBeenCalledWith("/api/profiles", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: expect.any(String),
    });
  });

  it("throws on error response", async () => {
    mockFetch.mockResolvedValue({ ok: false, status: 500 });
    await expect(
      saveProfile({
        profile: {
          name: "x",
          machine: "",
          temperatures: [],
          events: [],
          controls: {},
        },
      }),
    ).rejects.toThrow("Save failed: 500");
  });
});

describe("listProfiles", () => {
  it("returns profile summaries", async () => {
    const summaries = [
      {
        id: "1",
        name: "Test",
        machine: "",
        created_at: "",
        bean_name: "",
        data_points: 0,
      },
    ];
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(summaries),
    });

    const result = await listProfiles();
    expect(result).toEqual(summaries);
    expect(mockFetch).toHaveBeenCalledWith("/api/profiles");
  });
});

describe("getProfile", () => {
  it("fetches full profile by id", async () => {
    const profile = {
      id: "abc-123",
      name: "Test",
      machine: "Stratto",
      created_at: "2026-01-01",
      bean_name: "Ethiopian",
      temperatures: [],
      events: [],
      controls: { Burner: [[0, 50]] },
    };
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(profile),
    });

    const result = await getProfile("abc-123");
    expect(result).toEqual(profile);
    expect(mockFetch).toHaveBeenCalledWith("/api/profiles/abc-123");
  });

  it("throws on error response", async () => {
    mockFetch.mockResolvedValue({ ok: false, status: 404 });
    await expect(getProfile("nope")).rejects.toThrow("Get profile failed: 404");
  });
});

describe("deleteProfile", () => {
  it("sends DELETE request", async () => {
    mockFetch.mockResolvedValue({ ok: true });
    await deleteProfile("abc-123");
    expect(mockFetch).toHaveBeenCalledWith("/api/profiles/abc-123", {
      method: "DELETE",
    });
  });

  it("throws on error", async () => {
    mockFetch.mockResolvedValue({ ok: false, status: 404 });
    await expect(deleteProfile("nope")).rejects.toThrow("Delete failed: 404");
  });
});

// --- Schedules ---

describe("saveSchedule", () => {
  it("posts schedule and returns id", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: "sched-1" }),
    });

    const result = await saveSchedule({
      name: "Morning Roast",
      machine_name: "Stratto",
      steps: [
        {
          id: "s1",
          trigger: { type: "time", timestamp_ms: 0 },
          actions: [{ channel: "burner", value: 50 }],
          enabled: true,
        },
      ],
    });

    expect(result.id).toBe("sched-1");
    expect(mockFetch).toHaveBeenCalledWith("/api/schedules", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: expect.any(String),
    });
  });

  it("throws on error response", async () => {
    mockFetch.mockResolvedValue({ ok: false, status: 500 });
    await expect(
      saveSchedule({ name: "x", machine_name: "", steps: [] }),
    ).rejects.toThrow("Save schedule failed: 500");
  });
});

describe("listSchedules", () => {
  it("returns schedule summaries", async () => {
    const summaries = [
      {
        id: "1",
        name: "Morning",
        machine_name: "Stratto",
        created_at: "",
        step_count: 3,
      },
    ];
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(summaries),
    });

    const result = await listSchedules();
    expect(result).toEqual(summaries);
    expect(mockFetch).toHaveBeenCalledWith("/api/schedules");
  });
});

describe("getSchedule", () => {
  it("fetches full schedule by id", async () => {
    const schedule = {
      id: "sched-1",
      name: "Morning",
      machine_name: "Stratto",
      created_at: "2026-01-01",
      steps: [],
      source_profile_name: null,
    };
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(schedule),
    });

    const result = await getSchedule("sched-1");
    expect(result).toEqual(schedule);
    expect(mockFetch).toHaveBeenCalledWith("/api/schedules/sched-1");
  });

  it("throws on error response", async () => {
    mockFetch.mockResolvedValue({ ok: false, status: 404 });
    await expect(getSchedule("nope")).rejects.toThrow(
      "Get schedule failed: 404",
    );
  });
});

describe("deleteSchedule", () => {
  it("sends DELETE request", async () => {
    mockFetch.mockResolvedValue({ ok: true });
    await deleteSchedule("sched-1");
    expect(mockFetch).toHaveBeenCalledWith("/api/schedules/sched-1", {
      method: "DELETE",
    });
  });

  it("throws on error", async () => {
    mockFetch.mockResolvedValue({ ok: false, status: 404 });
    await expect(deleteSchedule("nope")).rejects.toThrow(
      "Delete schedule failed: 404",
    );
  });
});
