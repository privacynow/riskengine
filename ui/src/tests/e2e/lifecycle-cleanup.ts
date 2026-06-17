import type { APIRequestContext } from "@playwright/test";
import { LIFECYCLE_E2E_FIXTURE } from "./lifecycle-fixture";
import { requireAdminToken } from "./helpers";

/** Idempotent: reactivates the lifecycle scratch checkpoint if left deactivated. */
export async function ensureLifecycleFixtureActive(
  request: APIRequestContext,
): Promise<void> {
  const baseUrl = process.env.BASE_URL ?? "http://127.0.0.1:8000";
  const response = await request.post(
    `${baseUrl}/ui/checkpoints/${LIFECYCLE_E2E_FIXTURE.checkpointId}/reactivate`,
    {
      headers: {
        Authorization: `Bearer ${requireAdminToken()}`,
        "Content-Type": "application/json",
      },
      data: { promotion_reason: "Lifecycle e2e cleanup reactivate" },
    },
  );
  if (response.status() === 409) {
    return;
  }
  if (!response.ok()) {
    throw new Error(
      `Failed to reactivate lifecycle fixture checkpoint: HTTP ${response.status()}`
    );
  }
}
