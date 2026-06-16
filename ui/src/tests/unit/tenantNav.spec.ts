import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

const { mockRoute } = vi.hoisted(() => ({
  mockRoute: {
    currentRoute: {
      value: {
        query: {} as Record<string, string>,
        name: "overview",
        params: {},
      },
    },
  },
}));

vi.mock("@/app/router", () => ({
  default: mockRoute,
}));

import { routeWithTenant } from "@/app/tenantNav";
import { useTenantStore } from "@/stores/tenantStore";

describe("tenantNav", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    mockRoute.currentRoute.value.query = {};
  });

  it("adds active tenant id to route query", () => {
    const store = useTenantStore();
    store.activeTenant = { id: "tenant-a", name: "Tenant A" };
    const to = routeWithTenant({ name: "checkpoints" });
    expect(to).toMatchObject({ name: "checkpoints", query: { tenant: "tenant-a" } });
  });

  it("omits tenant query when none is active", () => {
    const to = routeWithTenant({ name: "tenants" });
    expect(to).toMatchObject({ name: "tenants", query: {} });
  });

  it("prefers store tenant over stale route query", () => {
    mockRoute.currentRoute.value.query = { tenant: "old-id" };
    const store = useTenantStore();
    store.activeTenant = { id: "new-id", name: "New" };
    const to = routeWithTenant({ name: "signals" });
    expect(to).toMatchObject({ query: { tenant: "new-id" } });
  });
});
