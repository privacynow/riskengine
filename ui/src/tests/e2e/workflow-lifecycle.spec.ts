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
  await page.waitForSelector(".signals-view .resource-table tbody tr", { timeout: 10000 });

  await navigateSidebar(page, "Decision Flows");
  await page.waitForSelector(".checkpoints-view", { timeout: 10000 });
  await page.getByRole("button", { name: "Load all" }).click();
  await page.waitForSelector(".checkpoints-view .resource-table tbody tr", { timeout: 10000 });

  await navigateSidebar(page, "Test Lab");
  await page.waitForSelector(".decision-test-view", { timeout: 10000 });
  await page.getByRole("button", { name: "Load all" }).click();
  await page.waitForSelector(".decision-test-view .resource-table tbody tr", { timeout: 10000 });
  await page.locator(".decision-test-view .entity-table-row").first().click();
  await page.getByRole("button", { name: "Run test" }).click();
  await page.waitForSelector(".decision-result", { timeout: 30000 });

  await navigateSidebar(page, "Audit");
  await page.waitForSelector(".audit-search-view", { timeout: 10000 });
  await page.getByRole("button", { name: "Search" }).click();
  await page.waitForSelector(".audit-search-view .resource-table tbody tr", { timeout: 10000 });
  await page.locator(".audit-search-view .entity-table-row").first().click();
  await expect(page.locator(".decision-detail-panel, .workbench-detail-body")).toBeVisible();
});
