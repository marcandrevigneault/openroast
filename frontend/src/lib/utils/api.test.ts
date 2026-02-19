import { describe, it, expect, vi, beforeEach } from "vitest";
import { saveProfile, listProfiles, deleteProfile } from "./api";

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
