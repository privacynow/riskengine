import { defineConfig, devices } from "@playwright/test";

const baseHost = (process.env.BASE_URL || "http://localhost:8000").replace(/\/$/, "");

export default defineConfig({
  testDir: "src/tests/e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: baseHost,
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
