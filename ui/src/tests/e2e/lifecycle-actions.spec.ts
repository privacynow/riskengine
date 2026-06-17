import { test, expect } from "@playwright/test";
import {
  authenticate,
  navigateSidebar,
  requireAdminToken,
  selectVisualFixtureTenant,
} from "./helpers";
import { LIFECYCLE_E2E_FIXTURE } from "./lifecycle-fixture";
import { ensureLifecycleFixtureActive } from "./lifecycle-cleanup";

test.beforeAll(() => {
  requireAdminToken();
});

test.afterEach(async ({ request }) => {
  await ensureLifecycleFixtureActive(request);
});

test("checkpoint lifecycle: deactivate and reactivate scratch checkpoint", async ({ page }) => {
  await authenticate(page);
  await selectVisualFixtureTenant(page);

  await navigateSidebar(page, "Checkpoints");
  await page.waitForSelector(".checkpoints-view", { timeout: 10000 });
  await page.getByRole("button", { name: "Load all" }).click();
  await page.waitForSelector(".checkpoints-view .list-row", { timeout: 10000 });

  const row = page.locator(".checkpoints-view .list-row", {
    hasText: LIFECYCLE_E2E_FIXTURE.checkpointName,
  });
  const deactivate = row.locator(".list-row-promote", { hasText: "Deactivate" });
  await expect(deactivate).toBeVisible();
  await deactivate.click();

  await page.locator(".modal-content input, .modal-content textarea").first().fill(
    "Lifecycle e2e deactivate"
  );
  await page.getByRole("button", { name: "Deactivate", exact: true }).click();
  await expect(row.locator(".list-row-promote", { hasText: "Reactivate" })).toBeVisible();

  const reactivate = row.locator(".list-row-promote", { hasText: "Reactivate" });
  await reactivate.click();
  await page.locator(".modal-content input, .modal-content textarea").first().fill(
    "Lifecycle e2e reactivate"
  );
  await page.getByRole("button", { name: "Reactivate", exact: true }).click();
  await expect(row.locator(".list-row-promote", { hasText: "Deactivate" })).toBeVisible();
});
