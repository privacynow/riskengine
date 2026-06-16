import { useTenantStore } from "@/stores/tenantStore";

/** Returns active tenant id or null when unset. */
export function activeTenantId(): string | null {
  const id = useTenantStore().activeTenantId;
  return id || null;
}

/** Returns tenant id for tenant-scoped API calls; null clears caller state. */
export function requireTenantId(): string | null {
  return activeTenantId();
}
