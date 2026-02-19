import { svelteTesting } from "@testing-library/svelte/vite";
import { sveltekit } from "@sveltejs/kit/vite";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [sveltekit(), svelteTesting()],
  test: {
    include: ["src/**/*.test.ts"],
    environment: "jsdom",
    setupFiles: ["./vitest-setup.ts"],
  },
});
