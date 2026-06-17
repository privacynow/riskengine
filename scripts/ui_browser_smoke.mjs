#!/usr/bin/env node
/**
 * Browser smoke for Decision Engine admin UI (Vue 3 + Vite build).
 * Env: BASE_URL, SMOKE_ADMIN_TOKEN
 *
 * Prefer stable routes/view classes over exact button copy. Nav labels are asserted
 * separately so terminology updates fail in one obvious place, not mid-navigation.
 */

import { chromium } from "playwright";

const BASE_URL = process.env.BASE_URL || "http://localhost:8000";
const ADMIN_TOKEN = process.env.SMOKE_ADMIN_TOKEN || "";
const AUTH_KEY = "decisionEngineAdminToken";

/** Keep in sync with ui/src/components/layout/SidebarNav.vue design section labels. */
const NAV_LABELS = {
  checkpoints: "Checkpoints",
  signals: "Signal Library",
};

const ALLOWED_CONSOLE_PATTERNS = [
  /favicon/i,
  /DevTools/i,
];

function fail(message) {
  console.error("Browser UI smoke failed:", message);
  process.exit(1);
}

function isAllowedConsoleMessage(text) {
  return ALLOWED_CONSOLE_PATTERNS.some((pattern) => pattern.test(text));
}

async function selectFirstTenant(page) {
  await page.waitForSelector("#tenant-select", { timeout: 10000 });
  const tenantValue = await page.evaluate(() => {
    const select = document.querySelector("#tenant-select");
    if (!select) return "";
    const option = Array.from(select.options).find((o) => o.value);
    return option ? option.value : "";
  });
  if (!tenantValue) {
    fail("no tenant options loaded in #tenant-select");
  }
  await page.selectOption("#tenant-select", tenantValue);
}

async function assertNoHorizontalOverflow(page) {
  const metrics = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }));
  if (metrics.scrollWidth > metrics.clientWidth + 1) {
    fail(
      `horizontal overflow at 390px: scrollWidth=${metrics.scrollWidth} clientWidth=${metrics.clientWidth}`
    );
  }
}

async function navigateSidebarRoute(page, routeSegment) {
  const link = page.locator(`.sidebar-nav a[href*="/admin/${routeSegment}"]`).first();
  await link.click();
  return link;
}

async function assertNavLabel(link, expectedLabel) {
  const label = (await link.locator(".nav-label").textContent())?.trim() ?? "";
  if (label !== expectedLabel) {
    fail(`nav label for ${expectedLabel} expected "${expectedLabel}", got "${label}"`);
  }
}

async function openWorkbenchCreateForm(page, viewClass, formClass) {
  await page.locator(`.${viewClass} .btn-primary`).click();
  await page.waitForSelector(`.${formClass}`, { timeout: 10000 });
}

async function main() {
  if (!ADMIN_TOKEN) {
    fail("SMOKE_ADMIN_TOKEN is required");
  }

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const pageErrors = [];
  const consoleErrors = [];

  page.on("pageerror", (err) => {
    pageErrors.push(err.message || String(err));
  });
  page.on("console", (msg) => {
    if (msg.type() !== "error") return;
    const text = msg.text();
    if (!isAllowedConsoleMessage(text)) {
      consoleErrors.push(text);
    }
  });

  try {
    console.log("-> Load /admin/ and authenticate");
    await page.goto(`${BASE_URL}/admin/`, { waitUntil: "networkidle" });
    await page.evaluate(
      ({ key, token }) => sessionStorage.setItem(key, token),
      { key: AUTH_KEY, token: ADMIN_TOKEN }
    );
    await page.reload({ waitUntil: "networkidle" });

    console.log("-> Assert app shell and routed content");
    await page.waitForSelector(".app-shell", { timeout: 15000 });
    await page.waitForSelector(".top-bar", { timeout: 10000 });
    await page.waitForSelector(".context-chip", { timeout: 10000 });
    await page.waitForSelector("main.page-content", { timeout: 10000 });
    await page.waitForSelector(".overview-view", { timeout: 10000 });

    if ((await page.locator("main.page-content .overview-view").count()) < 1) {
      fail("overview view not rendered inside main.page-content");
    }

    console.log("-> Select tenant");
    await selectFirstTenant(page);
    await page.waitForSelector(".overview-view .stat-grid", { timeout: 10000 });
    if ((await page.locator(".stat-card").count()) < 6) {
      fail("overview stat cards missing");
    }

    console.log("-> Navigate to Signal Library and open create form");
    const signalsLink = await navigateSidebarRoute(page, "signals");
    await assertNavLabel(signalsLink, NAV_LABELS.signals);
    await page.waitForSelector(".signals-view", { timeout: 10000 });
    await openWorkbenchCreateForm(page, "signals-view", "signal-form");

    const signalLabels = await page.locator(".signal-form label").allTextContents();
    for (const label of ["Name", "Description", "Type", "Cost"]) {
      if (!signalLabels.some((text) => text.includes(label))) {
        fail(`signal create form missing label: ${label}`);
      }
    }

    console.log("-> Navigate to Checkpoints and open create form");
    const checkpointsLink = await navigateSidebarRoute(page, "checkpoints");
    await assertNavLabel(checkpointsLink, NAV_LABELS.checkpoints);
    await page.waitForSelector(".checkpoints-view", { timeout: 10000 });
    await openWorkbenchCreateForm(page, "checkpoints-view", "checkpoint-form");

    const checkpointLabels = await page.locator(".checkpoint-form label").allTextContents();
    for (const label of ["Name", "DSL expression"]) {
      if (!checkpointLabels.some((text) => text.includes(label))) {
        fail(`checkpoint create form missing label: ${label}`);
      }
    }
    if ((await page.locator(".checkpoint-signals-panel").count()) < 1) {
      fail("checkpoint create form missing signal association panel");
    }

    console.log("-> Mobile overflow check (390px) after forms loaded");
    await page.setViewportSize({ width: 390, height: 844 });
    await page.waitForTimeout(400);
    await assertNoHorizontalOverflow(page);

    if (pageErrors.length) {
      fail(`page errors:\n${pageErrors.join("\n")}`);
    }
    if (consoleErrors.length) {
      fail(`console errors:\n${consoleErrors.join("\n")}`);
    }

    console.log("Browser UI smoke passed.");
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
