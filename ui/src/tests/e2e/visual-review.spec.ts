import { test, expect, type Page } from "@playwright/test";
import { authenticate, assertNoHorizontalOverflow, firstTenantId, selectTenant } from "./helpers";

async function assertOverviewChrome(page: Page) {
  await expect(page.locator(".top-bar h2, .top-bar .page-header-subtitle")).toHaveCount(0);
  await expect(
    page.locator(".overview-view").getByRole("heading", { name: "Operations overview", exact: true })
  ).toHaveCount(1);

  const refreshBtn = page.locator(".overview-view").getByRole("button", { name: "Refresh" });
  await expect(refreshBtn).toBeVisible();
  const refreshRadius = await refreshBtn.evaluate((el) => getComputedStyle(el).borderRadius);
  expect(refreshRadius).not.toBe("0px");

  const testLabLink = page.locator(".overview-view").getByRole("link", { name: "Test Lab", exact: true });
  await expect(testLabLink).toBeVisible();
  const linkDecoration = await testLabLink.evaluate(
    (el) => getComputedStyle(el).textDecorationLine
  );
  expect(linkDecoration).not.toContain("underline");
  const linkRadius = await testLabLink.evaluate((el) => getComputedStyle(el).borderRadius);
  expect(linkRadius).not.toBe("0px");
}

async function assertOverviewPanelSpacing(page: Page) {
  const headers = page.locator(".overview-panels .panel-card-header");
  await expect(headers).toHaveCount(2);

  for (let i = 0; i < 2; i++) {
    const header = headers.nth(i);
    const paddingLeft = await header.evaluate((el) => parseFloat(getComputedStyle(el).paddingLeft));
    expect(paddingLeft).toBeGreaterThanOrEqual(12);

    const heading = header.locator("h4");
    await expect(heading).toHaveCount(1);
    const marginTop = await heading.evaluate((el) => parseFloat(getComputedStyle(el).marginTop));
    const marginBottom = await heading.evaluate((el) => parseFloat(getComputedStyle(el).marginBottom));
    expect(marginTop).toBe(0);
    expect(marginBottom).toBe(0);
  }

  await expect(page.locator(".overview-panels .resource-card-header")).toHaveCount(0);
}

async function assertOverviewListRows(page: Page) {
  const decisionRows = page.locator(".overview-panels .list-row");
  await expect(decisionRows.first()).toBeVisible();
  await expect(decisionRows.first().locator(".list-row-stats")).toHaveCount(1);
}

async function assertEmptyStateTypography(page: Page) {
  const emptyTitles = page.locator(".overview-panel-empty .empty-state-title");
  if ((await emptyTitles.count()) === 0) return;

  const marginTop = await emptyTitles.first().evaluate((el) => parseFloat(getComputedStyle(el).marginTop));
  expect(marginTop).toBe(0);
}

async function assertMobileListRowArrowsHidden(page: Page) {
  const actions = page.locator(".overview-view .list-row-action");
  const count = await actions.count();
  expect(count).toBeGreaterThan(0);
  for (let i = 0; i < count; i++) {
    await expect(actions.nth(i)).toBeHidden();
  }
}

async function assertTopBarFits(page: Page) {
  const layout = await page.evaluate(() => {
    const bar = document.querySelector(".top-bar");
    const chip = document.querySelector(".context-chip");
    const signOut = Array.from(document.querySelectorAll(".top-bar button")).find(
      (btn) => btn.textContent?.trim() === "Sign out"
    );
    if (!bar || !chip || !signOut) return null;
    const barRect = bar.getBoundingClientRect();
    const chipRect = chip.getBoundingClientRect();
    const signOutRect = signOut.getBoundingClientRect();
    return {
      chipWithinBar: chipRect.top >= barRect.top - 1 && chipRect.bottom <= barRect.bottom + 1,
      signOutWithinBar: signOutRect.top >= barRect.top - 1 && signOutRect.bottom <= barRect.bottom + 1,
    };
  });
  expect(layout).not.toBeNull();
  expect(layout!.chipWithinBar).toBe(true);
  expect(layout!.signOutWithinBar).toBe(true);
}

async function assertWorkbenchDetailHeader(page: Page) {
  const header = page.locator(".workbench-detail-header").first();
  await expect(header).toBeVisible();
  const paddingLeft = await header.evaluate((el) => parseFloat(getComputedStyle(el).paddingLeft));
  expect(paddingLeft).toBeGreaterThanOrEqual(12);

  const heading = header.locator("h3").first();
  await expect(heading).toBeVisible();
  const marginTop = await heading.evaluate((el) => parseFloat(getComputedStyle(el).marginTop));
  expect(marginTop).toBe(0);
}

test.describe("visual review — overview", () => {
  test.beforeEach(async ({ page }) => {
    await authenticate(page);
    const tenantId = await firstTenantId(page);
    await selectTenant(page, tenantId);
    await page.waitForSelector(".overview-view .stat-grid", { timeout: 15000 });
  });

  test("overview desktop", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.waitForTimeout(300);
    await assertOverviewChrome(page);
    await assertOverviewPanelSpacing(page);
    await assertOverviewListRows(page);
    await assertEmptyStateTypography(page);
    await assertNoHorizontalOverflow(page);
    await expect(page.locator(".overview-view")).toBeVisible();
    await expect(page.locator(".overview-view")).toHaveScreenshot("overview-desktop.png");
  });

  test("overview mobile", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.waitForTimeout(300);
    await assertOverviewChrome(page);
    await assertOverviewPanelSpacing(page);
    await assertOverviewListRows(page);
    await assertMobileListRowArrowsHidden(page);
    await assertTopBarFits(page);
    await assertNoHorizontalOverflow(page);
    await expect(page.locator(".overview-view")).toBeVisible();
    await expect(page.locator(".overview-view")).toHaveScreenshot("overview-mobile-390.png");
  });
});

test.describe("visual review — workbench", () => {
  test.beforeEach(async ({ page }) => {
    await authenticate(page);
    const tenantId = await firstTenantId(page);
    await selectTenant(page, tenantId);
  });

  test("workbench detail header spacing", async ({ page }) => {
    await page.getByRole("link", { name: "Decision Flows", exact: true }).click();
    await page.waitForSelector(".checkpoints-view", { timeout: 10000 });
    await page.locator(".checkpoints-view .list-row").first().click();
    await page.waitForSelector(".workbench-detail-header", { timeout: 10000 });
    await assertWorkbenchDetailHeader(page);
  });

  test("flows and signals list rows", async ({ page }) => {
    await page.getByRole("link", { name: "Decision Flows", exact: true }).click();
    await page.waitForSelector(".checkpoints-view .list-row", { timeout: 10000 });
    await expect(page.locator(".checkpoints-view .list-row").first()).toBeVisible();

    await page.getByRole("link", { name: "Signal Library", exact: true }).click();
    await page.waitForSelector(".signals-view .list-row", { timeout: 10000 });
    await expect(page.locator(".signals-view .list-row").first()).toBeVisible();
  });
});
