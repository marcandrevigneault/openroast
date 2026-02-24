import { describe, it, expect, vi, beforeEach } from "vitest";
import { svgToPng, downloadBlob, exportChartPng } from "./chart-export";

describe("downloadBlob", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("creates a download link and clicks it", () => {
    const revokeUrl = vi.fn();
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:test-url");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(revokeUrl);

    const appendChild = vi.spyOn(document.body, "appendChild");
    const removeChild = vi.spyOn(document.body, "removeChild");

    const blob = new Blob(["test"], { type: "image/png" });
    downloadBlob(blob, "chart.png");

    expect(appendChild).toHaveBeenCalledOnce();
    const anchor = appendChild.mock.calls[0][0] as HTMLAnchorElement;
    expect(anchor.tagName).toBe("A");
    expect(anchor.download).toBe("chart.png");
    expect(anchor.href).toContain("blob:test-url");
    expect(removeChild).toHaveBeenCalledOnce();
    expect(revokeUrl).toHaveBeenCalledWith("blob:test-url");
  });
});

describe("exportChartPng", () => {
  it("returns false when container has no SVG", async () => {
    const div = document.createElement("div");
    const result = await exportChartPng(div, "test.png");
    expect(result).toBe(false);
  });
});

describe("svgToPng", () => {
  it("rejects when canvas context is unavailable", async () => {
    // Create a mock SVG
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("width", "100");
    svg.setAttribute("height", "50");
    document.body.appendChild(svg);

    // Mock canvas to return null context
    const origCreate = document.createElement.bind(document);
    vi.spyOn(document, "createElement").mockImplementation((tag: string) => {
      if (tag === "canvas") {
        const canvas = origCreate("canvas");
        vi.spyOn(canvas, "getContext").mockReturnValue(null);
        return canvas;
      }
      return origCreate(tag);
    });

    await expect(svgToPng(svg)).rejects.toThrow("Canvas context not available");

    document.body.removeChild(svg);
  });
});
