import { test, expect } from "@playwright/test";
import { authenticate, requireAdminToken, selectTenant } from "./helpers";

const SAMPLE_TENANT = "11111111-1111-1111-1111-111111111111";
const FUNDS_DISBURSEMENT_ID = "22222222-2222-2222-2222-222222222204";

test.beforeAll(() => {
  requireAdminToken();
});

test("test lab DSL preflight passes for seeded Funds Disbursement", async ({ page }) => {
  await authenticate(page);
  await selectTenant(page, SAMPLE_TENANT);
  await page.goto(
    `/admin/test-decisions?tenant=${SAMPLE_TENANT}&checkpoint=${FUNDS_DISBURSEMENT_ID}`
  );
  await page.waitForSelector(".decision-test-view", { timeout: 10000 });
  await expect(page.locator(".dsl-preflight-title")).toHaveText("DSL preflight passed", {
    timeout: 15000,
  });
});
