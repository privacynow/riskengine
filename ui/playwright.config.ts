import { defineConfig, devices } from "@playwright/test";

const baseHost = (process.env.BASE_URL || "http://localhost:8000").replace(/\/$/, "");
const screenshotMaxDiffPixelRatio = process.env.CI ? 0.06 : 0.02;

export default defineConfig({
  testDir: "src/tests/e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: "list",
  snapshotPathTemplate: "{testDir}/{testFileDir}/{testFileName}-snapshots/{arg}-{projectName}{ext}",
  use: {
    baseURL: baseHost,
    trace: "on-first-retry",
  },
  expect: {
    toHaveScreenshot: {
      // Local snapshots are often reviewed from macOS, while CI renders on Ubuntu.
      // Keep structural layout assertions strict and allow a narrow pixel delta for
      // cross-platform font metrics and antialiasing.
      maxDiffPixelRatio: screenshotMaxDiffPixelRatio,
      animations: "disabled",
    },
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
