import { describe, it, expect, vi, beforeEach } from "vitest";
import { listSimulators, startSimulator, stopSimulator } from "./simulator-api";

describe("simulator-api", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  function mockFetch(data: unknown, status = 200) {
    return vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: status >= 200 && status < 300,
        status,
        json: () => Promise.resolve(data),
      }),
    );
  }

  describe("listSimulators", () => {
    it("returns running simulators", async () => {
      const data = [
        {
          machine_id: "m1",
          catalog_id: "stratto-2.0",
          manufacturer_id: "carmomaq",
          name: "Carmomaq Stratto 2.0 (sim)",
          port: 5020,
          host: "127.0.0.1",
        },
      ];
      mockFetch(data);

      const result = await listSimulators();
      expect(result).toEqual(data);
      expect(fetch).toHaveBeenCalledWith("/api/simulator");
    });

    it("throws on error", async () => {
      mockFetch(null, 500);
      await expect(listSimulators()).rejects.toThrow();
    });
  });

  describe("startSimulator", () => {
    it("starts a simulator and returns info", async () => {
      const data = {
        machine_id: "m1",
        catalog_id: "stratto-2.0",
        manufacturer_id: "carmomaq",
        name: "Carmomaq Stratto 2.0 (sim)",
        port: 5020,
        host: "127.0.0.1",
      };
      mockFetch(data, 201);

      const result = await startSimulator({
        manufacturer_id: "carmomaq",
        model_id: "stratto-2.0",
      });
      expect(result).toEqual(data);
      expect(fetch).toHaveBeenCalledWith("/api/simulator/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          manufacturer_id: "carmomaq",
          model_id: "stratto-2.0",
        }),
      });
    });

    it("sends port when provided", async () => {
      mockFetch({}, 201);

      await startSimulator({
        manufacturer_id: "carmomaq",
        model_id: "stratto-2.0",
        port: 5025,
      });

      const callBody = JSON.parse(
        (fetch as ReturnType<typeof vi.fn>).mock.calls[0][1].body,
      );
      expect(callBody.port).toBe(5025);
    });

    it("sends name when provided", async () => {
      mockFetch({}, 201);

      await startSimulator({
        manufacturer_id: "carmomaq",
        model_id: "stratto-2.0",
        name: "My Custom Sim",
      });

      const callBody = JSON.parse(
        (fetch as ReturnType<typeof vi.fn>).mock.calls[0][1].body,
      );
      expect(callBody.name).toBe("My Custom Sim");
    });

    it("throws on not found (bad catalog ID)", async () => {
      mockFetch(null, 404);
      await expect(
        startSimulator({
          manufacturer_id: "bad",
          model_id: "bad",
        }),
      ).rejects.toThrow("not found");
    });
  });

  describe("stopSimulator", () => {
    it("stops a running simulator", async () => {
      mockFetch(null, 204);

      await stopSimulator("m1");
      expect(fetch).toHaveBeenCalledWith("/api/simulator/m1/stop", {
        method: "POST",
      });
    });

    it("throws on not found", async () => {
      mockFetch(null, 404);
      await expect(stopSimulator("m1")).rejects.toThrow("not found");
    });
  });
});
