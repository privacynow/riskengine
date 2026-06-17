import { expect } from "@playwright/test";
import type { APIRequestContext } from "@playwright/test";
import { LIFECYCLE_E2E_FIXTURE } from "./lifecycle-fixture";
import { requireAdminToken } from "./helpers";

type LifecycleApiRow = {
  id: string;
  is_current_version: boolean;
  name: string;
};

function apiBaseUrl(): string {
  return process.env.BASE_URL ?? "http://127.0.0.1:8000";
}

function adminHeaders(): Record<string, string> {
  return {
    Authorization: `Bearer ${requireAdminToken()}`,
    "Content-Type": "application/json",
  };
}

export async function fetchLifecycleCheckpoint(
  request: APIRequestContext,
): Promise<LifecycleApiRow> {
  const response = await request.get(
    `${apiBaseUrl()}/ui/checkpoints/${LIFECYCLE_E2E_FIXTURE.checkpointId}`,
    { headers: adminHeaders() },
  );
  expect(response.ok()).toBeTruthy();
  return response.json() as Promise<LifecycleApiRow>;
}

export async function fetchLifecycleSignal(
  request: APIRequestContext,
): Promise<LifecycleApiRow> {
  const response = await request.get(
    `${apiBaseUrl()}/ui/signals/${LIFECYCLE_E2E_FIXTURE.signalId}`,
    { headers: adminHeaders() },
  );
  expect(response.ok()).toBeTruthy();
  return response.json() as Promise<LifecycleApiRow>;
}

export async function assertLifecycleFixtureIsCurrent(
  request: APIRequestContext,
): Promise<void> {
  const checkpoint = await fetchLifecycleCheckpoint(request);
  expect(checkpoint.id).toBe(LIFECYCLE_E2E_FIXTURE.checkpointId);
  expect(checkpoint.name).toBe(LIFECYCLE_E2E_FIXTURE.checkpointName);
  expect(checkpoint.is_current_version).toBe(true);

  const signal = await fetchLifecycleSignal(request);
  expect(signal.id).toBe(LIFECYCLE_E2E_FIXTURE.signalId);
  expect(signal.name).toBe(LIFECYCLE_E2E_FIXTURE.signalName);
  expect(signal.is_current_version).toBe(true);
}

async function reactivateLifecycleSignal(request: APIRequestContext): Promise<void> {
  const response = await request.post(
    `${apiBaseUrl()}/ui/signals/${LIFECYCLE_E2E_FIXTURE.signalId}/reactivate`,
    {
      headers: adminHeaders(),
      data: { promotionReason: "Lifecycle e2e cleanup reactivate signal" },
    },
  );
  if (response.status() === 409) {
    return;
  }
  if (!response.ok()) {
    throw new Error(
      `Failed to reactivate lifecycle fixture signal: HTTP ${response.status()}`
    );
  }
}

/** Idempotent: reactivates scratch checkpoint and signal if left deactivated. */
export async function ensureLifecycleFixtureActive(
  request: APIRequestContext,
): Promise<void> {
  const checkpointResponse = await request.post(
    `${apiBaseUrl()}/ui/checkpoints/${LIFECYCLE_E2E_FIXTURE.checkpointId}/reactivate`,
    {
      headers: adminHeaders(),
      data: { promotionReason: "Lifecycle e2e cleanup reactivate checkpoint" },
    },
  );
  if (checkpointResponse.status() !== 409 && !checkpointResponse.ok()) {
    throw new Error(
      `Failed to reactivate lifecycle fixture checkpoint: HTTP ${checkpointResponse.status()}`
    );
  }
  await reactivateLifecycleSignal(request);
}

export async function resetLifecycleFixtureForTest(
  request: APIRequestContext,
): Promise<void> {
  await ensureLifecycleFixtureActive(request);
  await assertLifecycleFixtureIsCurrent(request);
}
