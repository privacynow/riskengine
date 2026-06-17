import { test, expect } from "@playwright/test";
import {
  authenticate,
  AUTH_KEY,
  firstTenantId,
  navigateSidebar,
  requireAdminToken,
  selectTenant,
} from "./helpers";

/** Demo seed tenant from scripts/create_demo_env.sh / conftest SAMPLE_TENANT */
const DEMO_TENANT_ID = "11111111-1111-1111-1111-111111111111";

test.beforeAll(() => {
  requireAdminToken();
});

test.beforeEach(async ({ page }) => {
  await page.goto("/admin/");
  await page.evaluate(() => sessionStorage.clear());
});

test("deep link to checkpoints loads after auth bootstrap", async ({ page }) => {
  const token = requireAdminToken();
  await page.addInitScript(
    ({ key, value }) => sessionStorage.setItem(key, value),
    { key: AUTH_KEY, value: token }
  );

  await page.goto(`/admin/checkpoints?tenant=${DEMO_TENANT_ID}`, { waitUntil: "networkidle" });
  await page.waitForSelector(".app-shell", { timeout: 15000 });
  await page.waitForSelector(".checkpoints-view", { timeout: 10000 });
  await expect(page.locator("#tenant-select")).toHaveValue(DEMO_TENANT_ID);
  await expect(page.locator(".checkpoints-view .empty-state")).toHaveCount(0);
});

test("auth modal then deep link preserves route and loads data", async ({ page }) => {
  const token = requireAdminToken();
  await page.goto("/admin/signals", { waitUntil: "domcontentloaded" });
  await page.waitForSelector(".modal-content", { timeout: 10000 });

  await page.fill("#auth-token", token);
  await page.getByRole("button", { name: "Continue" }).click();
  await page.waitForSelector(".app-shell", { timeout: 15000 });
  await page.waitForURL(/\/admin\/signals/, { timeout: 10000 });
  await page.waitForSelector(".signals-view", { timeout: 10000 });

  const tenantId = await firstTenantId(page);
  await selectTenant(page, tenantId);
  await expect(page.locator(".signals-view .empty-state")).toHaveCount(0);
});

test("tenant switch reloads checkpoints list once", async ({ page }) => {
  await authenticate(page);
  const tenantId = await firstTenantId(page);
  await selectTenant(page, tenantId);

  await navigateSidebar(page, "Checkpoints");
  await page.waitForSelector(".checkpoints-view", { timeout: 10000 });

  const firstResponse = page.waitForResponse(
    (resp) =>
      resp.url().includes("/ui/checkpoints") &&
      resp.url().includes(`tenant_id=${tenantId}`) &&
      resp.ok()
  );
  await page.getByRole("button", { name: "Load all" }).click();
  await firstResponse;

  const otherTenantId = await page.$eval("#tenant-select", (select) => {
    const el = select as HTMLSelectElement;
    const options = Array.from(el.options).filter((o) => o.value);
    return options.length > 1 ? options[1].value : "";
  });

  test.skip(!otherTenantId, "Need at least two tenants for switch test");

  let checkpointFetchCount = 0;
  const onResponse = (resp: { url: () => string; ok: () => boolean }) => {
    if (
      resp.url().includes("/ui/checkpoints") &&
      resp.url().includes(`tenant_id=${otherTenantId}`) &&
      resp.ok()
    ) {
      checkpointFetchCount += 1;
    }
  };
  page.on("response", onResponse);

  const reloadResponse = page.waitForResponse(
    (resp) =>
      resp.url().includes("/ui/checkpoints") &&
      resp.url().includes(`tenant_id=${otherTenantId}`) &&
      resp.ok()
  );
  await selectTenant(page, otherTenantId!);
  await reloadResponse;
  page.off("response", onResponse);

  expect(checkpointFetchCount).toBe(1);
  await expect(page.locator("#tenant-select")).toHaveValue(otherTenantId!);
});

test("sidebar navigation preserves tenant query", async ({ page }) => {
  await authenticate(page);
  const tenantId = await firstTenantId(page);
  await selectTenant(page, tenantId);

  await navigateSidebar(page, "Signal Library");
  await page.waitForURL(new RegExp(`tenant=${tenantId}`));

  await navigateSidebar(page, "Checkpoints");
  await expect(page).toHaveURL(new RegExp(`tenant=${tenantId}`));
});

test("mobile checkpoints list renders list rows", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await authenticate(page);
  const tenantId = await firstTenantId(page);
  await selectTenant(page, tenantId);

  await navigateSidebar(page, "Checkpoints");
  await page.waitForSelector(".checkpoints-view", { timeout: 10000 });
  await page.getByRole("button", { name: "Load all" }).click();
  await page.waitForSelector(".checkpoints-view .list-row", { timeout: 10000 });
  expect(await page.locator(".checkpoints-view .list-row").count()).toBeGreaterThan(0);
});

test("mobile tenants list renders cards", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await authenticate(page);

  await navigateSidebar(page, "Tenants");
  await page.waitForSelector(".tenants-view", { timeout: 10000 });
  await page.getByRole("button", { name: "Load all" }).click();
  await page.waitForSelector(".resource-card-list .resource-card", { timeout: 10000 });
  expect(await page.locator(".resource-card-list .resource-card").count()).toBeGreaterThan(0);
});

test("missing static asset returns 404 not SPA shell", async ({ request, baseURL }) => {
  const host = (baseURL || "http://localhost:8000").replace(/\/$/, "");
  const resp = await request.get(`${host}/admin/assets/missing-bundle-deadbeef.js`);
  expect(resp.status()).toBe(404);
  const body = await resp.text();
  expect(body).not.toContain("Decision Engine Admin");
});
