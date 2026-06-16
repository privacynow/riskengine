import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import type { RouteLocationNormalizedLoaded } from "vue-router";

const { mockRoute } = vi.hoisted(() => ({
  mockRoute: {
    currentRoute: {
      value: {
        query: {} as Record<string, string>,
        name: "checkpoints",
        params: {},
      },
    },
    replace: vi.fn(),
  },
}));

vi.mock("@/app/router", () => ({
  default: mockRoute,
}));

vi.mock("@/api/tenantsApi", () => ({
  tenantsApi: { list: vi.fn() },
}));

import { useTenantStore } from "@/stores/tenantStore";

describe("tenantStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    mockRoute.currentRoute.value.query = {};
    mockRoute.replace.mockReset();
  });

  it("syncTenantFromRoute clears active tenant when query is absent", () => {
    const store = useTenantStore();
    store.allTenants = [{ id: "t1", name: "T1" }];
    store.activeTenant = { id: "t1", name: "T1" };
    store.syncTenantFromRoute(mockRoute.currentRoute.value as RouteLocationNormalizedLoaded);
    expect(store.activeTenant).toBeNull();
  });

  it("syncTenantFromRoute sets active tenant from query", () => {
    const store = useTenantStore();
    store.allTenants = [{ id: "t1", name: "T1" }];
    mockRoute.currentRoute.value.query = { tenant: "t1" };
    store.syncTenantFromRoute(mockRoute.currentRoute.value as RouteLocationNormalizedLoaded);
    expect(store.activeTenant?.id).toBe("t1");
  });
});
