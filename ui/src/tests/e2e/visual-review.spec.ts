import { test, expect, type Page } from "@playwright/test";
import { authenticate, assertNoHorizontalOverflow, firstTenantId, navigateSidebar, selectTenant, selectVisualFixtureTenant } from "./helpers";

async function neutralizePointer(page: Page) {
  await page.mouse.move(0, 0);
}

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
  const count = await decisionRows.count();
  if (count === 0) {
    await expect(page.locator(".overview-panel-empty .empty-state-title").first()).toBeVisible();
    return;
  }
  await expect(decisionRows.first()).toBeVisible();
  await expect(decisionRows.first().locator(".list-row-stats")).toHaveCount(1);
}

async function assertEmptyStateTypography(page: Page) {
  const emptyTitles = page.locator(".overview-panel-empty .empty-state-title");
  if ((await emptyTitles.count()) === 0) return;

  const marginTop = await emptyTitles.first().evaluate((el) => parseFloat(getComputedStyle(el).marginTop));
  expect(marginTop).toBe(0);
}

async function assertMobileListRowArrowsHidden(page: Page, root: string) {
  const actions = page.locator(`${root} .list-row-action`);
  const count = await actions.count();
  if (count === 0) return;
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

async function assertToolbarSearchHeight(page: Page, root: string) {
  const input = page.locator(`${root} input[type="search"].toolbar-grow`).first();
  await expect(input).toBeVisible();
  const height = await input.evaluate((el) => el.getBoundingClientRect().height);
  expect(height).toBeGreaterThan(30);
  expect(height).toBeLessThan(44);
}

async function assertSingleActiveNav(page: Page, label: string) {
  await expect(page.locator(".sidebar-nav-item.active")).toHaveCount(1);
  await expect(page.locator(".sidebar-nav-item.active", { hasText: label })).toHaveCount(1);
}

async function assertWorkbenchListRows(page: Page, root: string) {
  const row = page.locator(`${root} .list-row`).first();
  await expect(row).toBeVisible();
  await expect(row.locator(".list-row-stats")).toHaveCount(1);
  await expect(row.locator(".list-row-open")).toHaveCount(1);
}

async function prepareFlowsView(page: Page) {
  await navigateSidebar(page, "Decision Flows");
  await page.waitForSelector(".checkpoints-view", { timeout: 10000 });
  await page.locator(".checkpoints-view select.toolbar-select").selectOption("active");
  await page.locator(".checkpoints-view input[type='search'].toolbar-grow").fill("Onboarding");
  await page.getByRole("button", { name: "Search" }).click();
  await page.waitForSelector(".checkpoints-view .list-row", { timeout: 10000 });
}

async function prepareSignalsView(page: Page) {
  await navigateSidebar(page, "Signal Library");
  await page.waitForSelector(".signals-view", { timeout: 10000 });
  await page.locator(".signals-view input[type='search'].toolbar-grow").fill("age_check");
  await page.getByRole("button", { name: "Search" }).click();
  await page.waitForSelector(".signals-view .list-row", { timeout: 10000 });
}

test.describe("visual review — overview", () => {
  test.beforeEach(async ({ page }) => {
    await authenticate(page);
    await selectVisualFixtureTenant(page);
    await page.waitForSelector(".overview-view .stat-grid", { timeout: 15000 });
  });

  test("overview desktop", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.waitForTimeout(300);
    await neutralizePointer(page);
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
    await neutralizePointer(page);
    await assertOverviewChrome(page);
    await assertOverviewPanelSpacing(page);
    await assertOverviewListRows(page);
    await assertMobileListRowArrowsHidden(page, ".overview-view");
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
    await prepareFlowsView(page);
    await page.locator(".checkpoints-view .list-row-open").first().click();
    await page.waitForSelector(".workbench-detail-header", { timeout: 10000 });
    await assertWorkbenchDetailHeader(page);
  });

  test("flows desktop", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await prepareFlowsView(page);
    await page.waitForTimeout(300);
    await neutralizePointer(page);
    await assertSingleActiveNav(page, "Decision Flows");
    await assertWorkbenchListRows(page, ".checkpoints-view");
    await assertNoHorizontalOverflow(page);
    await expect(page.locator(".checkpoints-view")).toHaveScreenshot("flows-desktop.png");
  });

  test("flows mobile", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await prepareFlowsView(page);
    await page.waitForTimeout(300);
    await neutralizePointer(page);
    await assertSingleActiveNav(page, "Decision Flows");
    await assertToolbarSearchHeight(page, ".checkpoints-view");
    await assertWorkbenchListRows(page, ".checkpoints-view");
    await assertMobileListRowArrowsHidden(page, ".checkpoints-view");
    await assertNoHorizontalOverflow(page);
    await expect(page.locator(".checkpoints-view")).toHaveScreenshot("flows-mobile-390.png");
  });

  test("promote does not open row on Space", async ({ page }) => {
    await navigateSidebar(page, "Decision Flows");
    await page.waitForSelector(".checkpoints-view", { timeout: 10000 });
    await page.getByRole("button", { name: "Load all" }).click();
    await page.waitForSelector(".checkpoints-view .list-row", { timeout: 10000 });
    const promote = page.locator(".checkpoints-view .list-row-promote").first();
    if ((await promote.count()) === 0) {
      test.skip();
      return;
    }
    await promote.focus();
    await page.keyboard.press("Space");
    await expect(page).toHaveURL(/\/admin\/checkpoints/);
    await expect(page).not.toHaveURL(/checkpoint-detail/);
  });

  test("signals desktop", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await prepareSignalsView(page);
    await page.waitForTimeout(300);
    await neutralizePointer(page);
    await assertSingleActiveNav(page, "Signal Library");
    await assertWorkbenchListRows(page, ".signals-view");
    await assertNoHorizontalOverflow(page);
    await expect(page.locator(".signals-view")).toHaveScreenshot("signals-desktop.png");
  });

  test("signals mobile", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await prepareSignalsView(page);
    await page.waitForTimeout(300);
    await neutralizePointer(page);
    await assertSingleActiveNav(page, "Signal Library");
    await assertToolbarSearchHeight(page, ".signals-view");
    await assertWorkbenchListRows(page, ".signals-view");
    await assertMobileListRowArrowsHidden(page, ".signals-view");
    await assertNoHorizontalOverflow(page);
    await expect(page.locator(".signals-view")).toHaveScreenshot("signals-mobile-390.png");
  });
});

async function prepareAuditPromotionsView(page: Page) {
  await navigateSidebar(page, "Audit");
  await page.waitForSelector(".audit-search-view", { timeout: 10000 });
  await page.locator(".audit-search-view select.toolbar-select").selectOption("promotions");
  await page.getByRole("button", { name: "Search" }).click();
  await page.waitForSelector(".audit-search-view .list-row", { timeout: 15000 });
}

async function prepareTestLabView(page: Page) {
  await navigateSidebar(page, "Test Lab");
  await page.waitForSelector(".decision-test-view", { timeout: 10000 });
  await page.getByRole("button", { name: "Load all" }).click();
  await page.waitForSelector(".decision-test-view .list-row", { timeout: 10000 });
}

async function prepareAssociationsView(page: Page) {
  await navigateSidebar(page, "Relationships");
  await page.waitForSelector(".associations-view", { timeout: 10000 });
  await page.getByRole("button", { name: "Search" }).click();
  await page.waitForTimeout(500);
}

async function prepareTenantsView(page: Page) {
  await navigateSidebar(page, "Tenants");
  await page.waitForSelector(".tenants-view", { timeout: 10000 });
  await page.getByRole("button", { name: "Load all" }).click();
  await page.waitForTimeout(500);
}

test.describe("visual review — operate workbenches", () => {
  test.beforeEach(async ({ page }) => {
    await authenticate(page);
    const tenantId = await firstTenantId(page);
    await selectTenant(page, tenantId);
  });

  test("audit desktop", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await selectVisualFixtureTenant(page);
    await prepareAuditPromotionsView(page);
    await page.waitForTimeout(300);
    await neutralizePointer(page);
    await assertSingleActiveNav(page, "Audit");
    await assertWorkbenchListRows(page, ".audit-search-view");
    await assertNoHorizontalOverflow(page);
    await expect(page.locator(".audit-search-view")).toHaveScreenshot("audit-desktop.png");
  });

  test("audit mobile", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await selectVisualFixtureTenant(page);
    await prepareAuditPromotionsView(page);
    await page.waitForTimeout(300);
    await neutralizePointer(page);
    await assertSingleActiveNav(page, "Audit");
    await assertToolbarSearchHeight(page, ".audit-search-view");
    await assertWorkbenchListRows(page, ".audit-search-view");
    await assertMobileListRowArrowsHidden(page, ".audit-search-view");
    await assertTopBarFits(page);
    await assertNoHorizontalOverflow(page);
    await expect(page.locator(".audit-search-view")).toHaveScreenshot("audit-mobile-390.png");
  });

  test("test lab desktop", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await prepareTestLabView(page);
    await page.locator(".decision-test-view .list-row-open").first().click();
    await page.waitForSelector(".test-harness", { timeout: 10000 });
    await page.waitForTimeout(300);
    await neutralizePointer(page);
    await assertSingleActiveNav(page, "Test Lab");
    await assertWorkbenchListRows(page, ".decision-test-view");
    await assertNoHorizontalOverflow(page);
    await expect(page.locator(".decision-test-view")).toHaveScreenshot("test-lab-desktop.png");
  });

  test("test lab mobile", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await prepareTestLabView(page);
    await page.locator(".decision-test-view .list-row-open").first().click();
    await page.waitForSelector(".test-harness", { timeout: 10000 });
    await page.waitForTimeout(300);
    await neutralizePointer(page);
    await assertSingleActiveNav(page, "Test Lab");
    await assertToolbarSearchHeight(page, ".decision-test-view");
    await assertWorkbenchListRows(page, ".decision-test-view");
    await assertMobileListRowArrowsHidden(page, ".decision-test-view");
    await assertNoHorizontalOverflow(page);
    await expect(page.locator(".decision-test-view")).toHaveScreenshot("test-lab-mobile-390.png");
  });

  test("relationships mobile", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await prepareAssociationsView(page);
    await page.waitForTimeout(300);
    await neutralizePointer(page);
    await assertSingleActiveNav(page, "Relationships");
    await assertToolbarSearchHeight(page, ".associations-view");
    await assertTopBarFits(page);
    await assertNoHorizontalOverflow(page);
    await expect(page.locator(".associations-view")).toHaveScreenshot("relationships-mobile-390.png");
  });

  test("tenants mobile", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await prepareTenantsView(page);
    await page.waitForTimeout(300);
    await neutralizePointer(page);
    await assertSingleActiveNav(page, "Tenants");
    await assertToolbarSearchHeight(page, ".tenants-view");
    await assertTopBarFits(page);
    await assertNoHorizontalOverflow(page);
    await expect(page.locator(".tenants-view")).toHaveScreenshot("tenants-mobile-390.png");
  });
});
