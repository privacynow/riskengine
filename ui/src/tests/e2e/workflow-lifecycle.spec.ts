import { test, expect } from "@playwright/test";
import {
  authenticate,
  firstTenantId,
  navigateSidebar,
  requireAdminToken,
  selectTenant,
} from "./helpers";

test.beforeAll(() => {
  requireAdminToken();
});

test("workflow: libraries, test lab, and audit detail", async ({ page }) => {
  await authenticate(page);
  const tenantId = await firstTenantId(page);
  await selectTenant(page, tenantId);

  await navigateSidebar(page, "Signal Library");
  await page.waitForSelector(".signals-view", { timeout: 10000 });
  await page.getByRole("button", { name: "Load all" }).click();
  await page.waitForSelector(".signals-view .list-row", { timeout: 10000 });

  await navigateSidebar(page, "Checkpoints");
  await page.waitForSelector(".checkpoints-view", { timeout: 10000 });
  await page.getByRole("button", { name: "Load all" }).click();
  await page.waitForSelector(".checkpoints-view .list-row", { timeout: 10000 });

  await navigateSidebar(page, "Test Lab");
  await page.waitForSelector(".decision-test-view", { timeout: 10000 });
  await page.getByRole("button", { name: "Load all" }).click();
  await page.waitForSelector(".decision-test-view .list-row", { timeout: 10000 });
  await page.locator(".decision-test-view .list-row-open").first().click();
  await page.getByRole("button", { name: "Run test decision" }).click();
  await page.waitForSelector(".decision-result", { timeout: 30000 });

  await navigateSidebar(page, "Audit");
  await page.waitForSelector(".audit-search-view", { timeout: 10000 });
  await page.waitForSelector(".audit-search-view .list-row", { timeout: 15000 });
  await page.locator(".audit-search-view .list-row-open").first().click();
  await expect(page.locator(".decision-detail-panel, .workbench-detail-body")).toBeVisible();
});
