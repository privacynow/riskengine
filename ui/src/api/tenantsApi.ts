import { buildQuery, httpJson } from "@/api/httpClient";
import type { Paginated, Tenant } from "@/api/types";

export const tenantsApi = {
  list(page: number, size: number) {
    return httpJson<Paginated<Tenant>>(`/ui/tenants${buildQuery({ page, size })}`);
  },
  search(q: string, page: number, size: number) {
    return httpJson<Paginated<Tenant>>(
      `/ui/search_tenants${buildQuery({ q, page, size })}`
    );
  },
  create(payload: { name: string; copyFromTenantId?: string }) {
    return httpJson<Tenant>("/ui/tenants", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  },
  update(id: string, payload: { name: string }) {
    return httpJson<Tenant>(`/ui/tenants/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  },
};
