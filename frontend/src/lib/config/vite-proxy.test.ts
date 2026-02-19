// @vitest-environment node
import { describe, it, expect } from "vitest";
import config from "../../../vite.config";

/**
 * Validates that vite.config.ts has the required proxy configuration
 * so that /api and /ws requests are forwarded to the FastAPI backend.
 */
describe("Vite proxy configuration", () => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const resolved = config as any;
  const proxy = resolved.server?.proxy;

  it("proxies /api to backend", () => {
    expect(proxy).toBeDefined();
    expect(proxy["/api"]).toBeDefined();
    expect(proxy["/api"].target).toBe("http://localhost:8000");
  });

  it("proxies /ws to backend with WebSocket support", () => {
    expect(proxy["/ws"]).toBeDefined();
    expect(proxy["/ws"].target).toBe("http://localhost:8000");
    expect(proxy["/ws"].ws).toBe(true);
  });
});
