import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./tests/setupTests.ts",
    include: ["tests/**/*.test.tsx", "tests/**/*.test.ts"],
    coverage: {
      reporter: ["text", "lcov"],
    },
  },
});
