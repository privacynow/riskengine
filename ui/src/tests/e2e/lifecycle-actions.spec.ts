import { test, expect } from "@playwright/test";
import {
  authenticate,
  navigateSidebar,
  requireAdminToken,
  selectVisualFixtureTenant,
} from "./helpers";
import { LIFECYCLE_E2E_FIXTURE } from "./lifecycle-fixture";
import {
  assertLifecycleFixtureIsCurrent,
  ensureLifecycleFixtureActive,
  resetLifecycleFixtureForTest,
} from "./lifecycle-cleanup";

test.beforeAll(() => {
  requireAdminToken();
});

test.beforeEach(async ({ request }) => {
  await resetLifecycleFixtureForTest(request);
});

test.afterEach(async ({ request }) => {
  await ensureLifecycleFixtureActive(request);
});

test("checkpoint lifecycle: deactivate and reactivate scratch checkpoint", async ({
  page,
  request,
}) => {
  await assertLifecycleFixtureIsCurrent(request);
  await authenticate(page);
  await selectVisualFixtureTenant(page);

  await navigateSidebar(page, "Checkpoints");
  await page.waitForSelector(".checkpoints-view", { timeout: 10000 });
  await page
    .locator(".checkpoints-view input[type='search'].toolbar-grow")
    .fill(LIFECYCLE_E2E_FIXTURE.checkpointName);
  await page.getByRole("button", { name: "Search" }).click();
  await page.waitForSelector(".checkpoints-view .list-row", { timeout: 10000 });

  const row = page.getByTestId(`checkpoint-row-${LIFECYCLE_E2E_FIXTURE.checkpointId}`);
  await expect(row).toHaveCount(1);
  const deactivate = row.getByTestId("checkpoint-deactivate");
  await expect(deactivate).toBeVisible();
  await deactivate.click();

  await page.locator(".modal-content input, .modal-content textarea").first().fill(
    "Lifecycle e2e deactivate"
  );
  await page
    .locator(".modal-content")
    .getByRole("button", { name: "Deactivate", exact: true })
    .click();
  await expect(row.getByTestId("checkpoint-reactivate")).toBeVisible();

  await row.getByTestId("checkpoint-reactivate").click();
  await page.locator(".modal-content input, .modal-content textarea").first().fill(
    "Lifecycle e2e reactivate"
  );
  await page
    .locator(".modal-content")
    .getByRole("button", { name: "Reactivate", exact: true })
    .click();
  await expect(row.getByTestId("checkpoint-deactivate")).toBeVisible();

  await assertLifecycleFixtureIsCurrent(request);
});

test("signal lifecycle: deactivate and reactivate scratch signal", async ({
  page,
  request,
}) => {
  await assertLifecycleFixtureIsCurrent(request);
  await authenticate(page);
  await selectVisualFixtureTenant(page);

  await navigateSidebar(page, "Signal Library");
  await page.waitForSelector(".signals-view", { timeout: 10000 });
  await page
    .locator(".signals-view input[type='search'].toolbar-grow")
    .fill(LIFECYCLE_E2E_FIXTURE.signalName);
  await page.getByRole("button", { name: "Search" }).click();
  await page.waitForSelector(".signals-view .list-row", { timeout: 10000 });

  const row = page.getByTestId(`signal-row-${LIFECYCLE_E2E_FIXTURE.signalId}`);
  await expect(row).toHaveCount(1);
  const deactivate = row.getByTestId("signal-deactivate");
  await expect(deactivate).toBeVisible();
  await deactivate.click();

  await page.locator(".modal-content input, .modal-content textarea").first().fill(
    "Lifecycle e2e deactivate signal"
  );
  await page
    .locator(".modal-content")
    .getByRole("button", { name: "Deactivate", exact: true })
    .click();
  await expect(row.getByTestId("signal-reactivate")).toBeVisible();

  await row.getByTestId("signal-reactivate").click();
  await page.locator(".modal-content input, .modal-content textarea").first().fill(
    "Lifecycle e2e reactivate signal"
  );
  await page
    .locator(".modal-content")
    .getByRole("button", { name: "Reactivate", exact: true })
    .click();
  await expect(row.getByTestId("signal-deactivate")).toBeVisible();

  await assertLifecycleFixtureIsCurrent(request);
});
