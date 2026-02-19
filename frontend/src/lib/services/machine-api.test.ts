import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  listManufacturers,
  listModels,
  listMachines,
  getMachine,
  createFromCatalog,
  createCustomMachine,
  deleteMachine,
  connectMachine,
  disconnectMachine,
  getMachineStatus,
} from "./machine-api";

describe("machine-api", () => {
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

  describe("listManufacturers", () => {
    it("returns manufacturer list", async () => {
      const data = [
        { id: "carmomaq", name: "Carmomaq", country: "BR", model_count: 3 },
      ];
      mockFetch(data);

      const result = await listManufacturers();
      expect(result).toEqual(data);
      expect(fetch).toHaveBeenCalledWith("/api/catalog/manufacturers");
    });

    it("throws on error", async () => {
      mockFetch(null, 500);
      await expect(listManufacturers()).rejects.toThrow();
    });
  });

  describe("listModels", () => {
    it("returns models for manufacturer", async () => {
      const data = [
        { id: "stratto", name: "Stratto 2.0", protocol: "modbus_tcp" },
      ];
      mockFetch(data);

      const result = await listModels("carmomaq");
      expect(result).toEqual(data);
      expect(fetch).toHaveBeenCalledWith(
        "/api/catalog/manufacturers/carmomaq/models",
      );
    });
  });

  describe("listMachines", () => {
    it("returns saved machines", async () => {
      const data = [{ id: "m1", name: "My Stratto", protocol: "modbus_tcp" }];
      mockFetch(data);

      const result = await listMachines();
      expect(result).toEqual(data);
    });
  });

  describe("getMachine", () => {
    it("returns machine details", async () => {
      const data = { id: "m1", name: "My Stratto", protocol: "modbus_tcp" };
      mockFetch(data);

      const result = await getMachine("m1");
      expect(result).toEqual(data);
      expect(fetch).toHaveBeenCalledWith("/api/machines/m1");
    });
  });

  describe("createFromCatalog", () => {
    it("creates machine from catalog", async () => {
      const data = { id: "m1", machine: { id: "m1", name: "Stratto" } };
      mockFetch(data);

      const result = await createFromCatalog(
        "carmomaq",
        "stratto-2.0",
        "My Stratto",
      );
      expect(result).toEqual(data);
      expect(fetch).toHaveBeenCalledWith("/api/machines/from-catalog", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          manufacturer_id: "carmomaq",
          model_id: "stratto-2.0",
          name: "My Stratto",
        }),
      });
    });

    it("omits name when not provided", async () => {
      mockFetch({ id: "m1", machine: {} });

      await createFromCatalog("carmomaq", "stratto-2.0");
      const callBody = JSON.parse(
        (fetch as ReturnType<typeof vi.fn>).mock.calls[0][1].body,
      );
      expect(callBody.name).toBeUndefined();
    });
  });

  describe("createCustomMachine", () => {
    it("creates custom machine via POST /machines", async () => {
      // First call: POST /machines returns { id }
      // Second call: GET /machines/{id} returns full machine
      const machine = {
        id: "m2",
        name: "My Roaster",
        protocol: "modbus_tcp",
        connection: { type: "modbus_tcp", host: "10.0.0.1", port: 502 },
        sampling_interval_ms: 3000,
        controls: [],
        extra_channels: [],
      };
      vi.stubGlobal(
        "fetch",
        vi
          .fn()
          .mockResolvedValueOnce({
            ok: true,
            status: 201,
            json: () => Promise.resolve({ id: "m2" }),
          })
          .mockResolvedValueOnce({
            ok: true,
            status: 200,
            json: () => Promise.resolve(machine),
          }),
      );

      const result = await createCustomMachine({
        name: "My Roaster",
        protocol: "modbus_tcp",
        connection: { type: "modbus_tcp", host: "10.0.0.1", port: 502 },
      });
      expect(result).toEqual({ id: "m2", machine });

      const calls = (fetch as ReturnType<typeof vi.fn>).mock.calls;
      expect(calls[0][0]).toBe("/api/machines");
      expect(calls[0][1].method).toBe("POST");
      expect(calls[1][0]).toBe("/api/machines/m2");
    });

    it("throws on error", async () => {
      mockFetch(null, 422);
      await expect(
        createCustomMachine({
          name: "",
          protocol: "modbus_tcp",
          connection: {},
        }),
      ).rejects.toThrow();
    });
  });

  describe("deleteMachine", () => {
    it("sends DELETE request", async () => {
      mockFetch(null, 204);

      await deleteMachine("m1");
      expect(fetch).toHaveBeenCalledWith("/api/machines/m1", {
        method: "DELETE",
      });
    });
  });

  describe("connectMachine", () => {
    it("sends POST to connect", async () => {
      const data = { status: "connected", machine_id: "m1" };
      mockFetch(data);

      const result = await connectMachine("m1");
      expect(result).toEqual(data);
      expect(fetch).toHaveBeenCalledWith("/api/machines/m1/connect", {
        method: "POST",
      });
    });

    it("throws with error detail on failure", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValue({
          ok: false,
          status: 502,
          json: () => Promise.resolve({ detail: "Cannot reach device" }),
        }),
      );

      await expect(connectMachine("m1")).rejects.toThrow("Cannot reach device");
    });
  });

  describe("disconnectMachine", () => {
    it("sends POST to disconnect", async () => {
      const data = { status: "disconnected", machine_id: "m1" };
      mockFetch(data);

      const result = await disconnectMachine("m1");
      expect(result).toEqual(data);
    });
  });

  describe("getMachineStatus", () => {
    it("returns machine status", async () => {
      const data = {
        machine_id: "m1",
        connected: true,
        driver_state: "connected",
        session_state: "idle",
      };
      mockFetch(data);

      const result = await getMachineStatus("m1");
      expect(result).toEqual(data);
    });
  });
});
