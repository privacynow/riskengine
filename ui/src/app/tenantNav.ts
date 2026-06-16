import type { RouteLocationRaw } from "vue-router";
import router from "@/app/router";
import { useTenantStore } from "@/stores/tenantStore";

/** Merge active tenant into a router destination query. */
export function routeWithTenant(to: RouteLocationRaw): RouteLocationRaw {
  if (typeof to === "string") return to;

  const tenantStore = useTenantStore();
  const routeTenant = router.currentRoute.value.query.tenant;
  const tenantId =
    tenantStore.activeTenantId ||
    (typeof routeTenant === "string" ? routeTenant : "");

  const query: Record<string, string> = {};
  for (const [key, value] of Object.entries(to.query ?? {})) {
    if (typeof value === "string") query[key] = value;
  }
  if (tenantId) query.tenant = tenantId;

  return { ...to, query };
}
