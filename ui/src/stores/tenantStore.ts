import { defineStore } from "pinia";
import type { Tenant } from "@/api/types";
import { DEFAULT_PAGE_SIZE } from "@/app/config";
import { totalPages } from "@/api/types";
import { tenantsApi } from "@/api/tenantsApi";
import { useAuthStore } from "@/stores/authStore";
import { useUiStore } from "@/stores/uiStore";
import type { RouteLocationNormalizedLoaded } from "vue-router";
import router from "@/app/router";

export const useTenantStore = defineStore("tenant", {
  state: () => ({
    allTenants: [] as Tenant[],
    activeTenant: null as Tenant | null,
    searchTerm: "",
    newTenantName: "",
    showCreateForm: false,
    copyFromTenantId: "",
    tenants: [] as Tenant[],
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    total: 0,
    totalPages: 1,
    loading: false,
    error: "",
    expanded: {} as Record<string, boolean>,
    edits: {} as Record<string, { name: string }>,
  }),
  getters: {
    activeTenantId: (state) => state.activeTenant?.id ?? "",
  },
  actions: {
    async fetchAllTenants() {
      try {
        const data = await tenantsApi.list(1, 9999);
        this.allTenants = data.items;
      } catch (err) {
        useAuthStore().handleApiError(err);
      }
    },

    syncTenantFromRoute(route: RouteLocationNormalizedLoaded = router.currentRoute.value) {
      const raw = route.query.tenant;
      const tenantId = Array.isArray(raw) ? raw[0] : raw;
      if (typeof tenantId !== "string" || !tenantId) {
        this.activeTenant = null;
        return;
      }
      const found = this.allTenants.find((t) => t.id === tenantId);
      this.activeTenant = found ?? null;
    },

    async setActiveTenant(tenant: Tenant | null) {
      this.activeTenant = tenant;
      const route = router.currentRoute.value;
      const query: Record<string, string> = {};
      for (const [key, value] of Object.entries(route.query)) {
        if (typeof value === "string") query[key] = value;
      }
      if (tenant?.id) query.tenant = tenant.id;
      else delete query.tenant;
      await router.replace({ name: route.name ?? undefined, params: route.params, query });
    },

    async fetchPage(page: number) {
      this.loading = true;
      this.error = "";
      this.page = page;
      try {
        const data = await tenantsApi.list(page, this.pageSize);
        this.tenants = data.items;
        this.total = data.total;
        this.totalPages = totalPages(data.total, this.pageSize);
      } catch (err) {
        useAuthStore().handleApiError(err);
        this.error = err instanceof Error ? err.message : "Failed to load tenants";
      } finally {
        this.loading = false;
      }
    },

    async search(page: number) {
      this.page = page;
      const q = this.searchTerm.trim();
      if (!q) {
        await this.fetchPage(page);
        return;
      }
      this.loading = true;
      this.error = "";
      try {
        const data = await tenantsApi.search(q, page, this.pageSize);
        this.tenants = data.items;
        this.total = data.total;
        this.totalPages = totalPages(data.total, this.pageSize);
      } catch (err) {
        useAuthStore().handleApiError(err);
        this.error = err instanceof Error ? err.message : "Search failed";
      } finally {
        this.loading = false;
      }
    },

    toggleCreateForm() {
      this.showCreateForm = !this.showCreateForm;
    },

    async createTenant() {
      const ui = useUiStore();
      try {
        await tenantsApi.create({
          name: this.newTenantName,
          copyFromTenantId: this.copyFromTenantId || undefined,
        });
        this.newTenantName = "";
        this.copyFromTenantId = "";
        this.showCreateForm = false;
        await this.fetchAllTenants();
        await this.fetchPage(this.page);
        ui.notify("Tenant created.");
      } catch (err) {
        useAuthStore().handleApiError(err);
      }
    },

    toggleExpand(id: string) {
      this.expanded[id] = !this.expanded[id];
      if (this.expanded[id] && !this.edits[id]) {
        const tenant = this.tenants.find((t) => t.id === id);
        if (tenant) this.edits[id] = { name: tenant.name };
      }
    },

    async saveTenant(id: string) {
      const edit = this.edits[id];
      if (!edit) return;
      const ui = useUiStore();
      try {
        await tenantsApi.update(id, { name: edit.name });
        this.expanded[id] = false;
        delete this.edits[id];
        await this.fetchPage(this.page);
        ui.notify("Tenant updated.");
      } catch (err) {
        useAuthStore().handleApiError(err);
      }
    },
  },
});
