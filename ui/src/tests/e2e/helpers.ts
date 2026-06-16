import type { Page } from "@playwright/test";
import { expect } from "@playwright/test";

export const AUTH_KEY = "decisionEngineAdminToken";
export const VISUAL_FIXTURE_TENANT = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";

export function requireAdminToken(): string {
  const token = process.env.SMOKE_ADMIN_TOKEN ?? "";
  if (!token) {
    throw new Error("SMOKE_ADMIN_TOKEN is required for e2e tests");
  }
  return token;
}

export async function authenticate(page: Page, token = requireAdminToken()): Promise<void> {
  await page.goto("/admin/");
  await page.evaluate(
    ({ key, value }) => sessionStorage.setItem(key, value),
    { key: AUTH_KEY, value: token }
  );
  await page.reload({ waitUntil: "networkidle" });
  await page.waitForSelector(".app-shell", { timeout: 15000 });
}

export async function firstTenantId(page: Page): Promise<string> {
  await page.waitForSelector("#tenant-select", { timeout: 10000 });
  const tenantId = await page.$eval("#tenant-select", (select) => {
    const el = select as HTMLSelectElement;
    const option = Array.from(el.options).find((o) => o.value);
    return option?.value ?? "";
  });
  expect(tenantId).toBeTruthy();
  return tenantId;
}

export async function openMobileNav(page: Page): Promise<void> {
  await page.getByRole("button", { name: "Open navigation" }).click();
  await page.waitForSelector(".sidebar-nav.open", { timeout: 5000 });
}

export async function navigateSidebar(page: Page, label: string): Promise<void> {
  const viewport = page.viewportSize();
  if (viewport && viewport.width <= 768) {
    await openMobileNav(page);
  }
  await page.locator(".sidebar-nav").getByRole("link", { name: label, exact: true }).click();
}

export async function assertNoHorizontalOverflow(page: Page): Promise<void> {
  const metrics = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }));
  expect(metrics.scrollWidth).toBeLessThanOrEqual(metrics.clientWidth + 1);
}

export async function selectTenant(page: Page, tenantId: string): Promise<void> {
  await page.selectOption("#tenant-select", tenantId);
  await page.waitForURL((url) => url.searchParams.get("tenant") === tenantId);
}

export async function selectVisualFixtureTenant(page: Page): Promise<void> {
  await selectTenant(page, VISUAL_FIXTURE_TENANT);
}
