import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { activeTenantId, requireTenantId } from "@/app/tenantScope";
import { useTenantStore } from "@/stores/tenantStore";

describe("tenantScope", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("returns null when no tenant is active", () => {
    expect(activeTenantId()).toBeNull();
    expect(requireTenantId()).toBeNull();
  });

  it("returns the active tenant id", () => {
    const store = useTenantStore();
    store.activeTenant = { id: "tenant-a", name: "Tenant A" };
    expect(activeTenantId()).toBe("tenant-a");
    expect(requireTenantId()).toBe("tenant-a");
  });
});
