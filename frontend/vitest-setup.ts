import "@testing-library/jest-dom/vitest";

// jsdom doesn't implement ResizeObserver — stub it for bind:clientWidth
if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}
