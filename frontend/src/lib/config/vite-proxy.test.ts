import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { resolve } from "path";

/**
 * Validates that vite.config.ts has the required proxy configuration
 * so that /api and /ws requests are forwarded to the FastAPI backend.
 */
describe("Vite proxy configuration", () => {
  const configPath = resolve(process.cwd(), "vite.config.ts");
  const configSource = readFileSync(configPath, "utf-8");

  it("proxies /api to backend", () => {
    expect(configSource).toContain('"/api"');
    expect(configSource).toContain("http://localhost:8000");
  });

  it("proxies /ws to backend with WebSocket support", () => {
    expect(configSource).toContain('"/ws"');
    expect(configSource).toMatch(/ws:\s*true/);
  });
});
