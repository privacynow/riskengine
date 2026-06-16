#!/usr/bin/env node
/**
 * Browser smoke for Decision Engine admin UI (Vue 3 + Vite build).
 * Env: BASE_URL, SMOKE_ADMIN_TOKEN
 */

import { chromium } from "playwright";

const BASE_URL = process.env.BASE_URL || "http://localhost:8000";
const ADMIN_TOKEN = process.env.SMOKE_ADMIN_TOKEN || "";
const AUTH_KEY = "decisionEngineAdminToken";

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
    await page.waitForSelector(".tenant-context-bar", { timeout: 10000 });
    await page.waitForSelector("main.page-content", { timeout: 10000 });
    await page.waitForSelector(".overview-view .stat-grid", { timeout: 10000 });

    if ((await page.locator("main.page-content .overview-view").count()) < 1) {
      fail("overview view not rendered inside main.page-content");
    }
    if ((await page.locator(".stat-card").count()) < 3) {
      fail("overview stat cards missing");
    }

    console.log("-> Select tenant");
    await selectFirstTenant(page);

    console.log("-> Navigate to Signals and open create form");
    await page.getByRole("button", { name: "Signals" }).click();
    await page.waitForSelector(".signals-view", { timeout: 10000 });
    await page.getByRole("button", { name: "Create signal" }).click();
    await page.waitForSelector(".signal-form", { timeout: 10000 });

    const signalLabels = await page.locator(".signal-form label").allTextContents();
    for (const label of ["Name", "Description", "Type", "Cost"]) {
      if (!signalLabels.some((text) => text.includes(label))) {
        fail(`signal create form missing label: ${label}`);
      }
    }

    console.log("-> Navigate to Checkpoints and open create form");
    await page.getByRole("button", { name: "Checkpoints" }).click();
    await page.waitForSelector(".checkpoints-view", { timeout: 10000 });
    await page.getByRole("button", { name: "Create checkpoint" }).click();
    await page.waitForSelector(".checkpoint-form", { timeout: 10000 });

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
