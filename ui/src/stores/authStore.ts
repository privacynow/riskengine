import { defineStore } from "pinia";
import { ApiError } from "@/api/errors";
import { httpRequest, setStoredToken } from "@/api/httpClient";
import { tenantsApi } from "@/api/tenantsApi";
import { useTenantStore } from "@/stores/tenantStore";
import { useUiStore } from "@/stores/uiStore";
import { loadRouteData } from "@/app/routeLoader";
import router from "@/app/router";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    isReady: false,
    showAuthPrompt: true,
    tokenInput: "",
    authError: "",
    sessionValidated: false,
  }),
  actions: {
    async initializeFromStorage() {
      if (this.sessionValidated) return;
      const token = sessionStorage.getItem("decisionEngineAdminToken");
      if (!token) {
        this.showAuthPrompt = true;
        return;
      }
      try {
        await tenantsApi.list(1, 1);
        this.showAuthPrompt = false;
        this.sessionValidated = true;
        await this.bootstrap();
      } catch {
        setStoredToken("");
        this.showAuthPrompt = true;
        this.sessionValidated = false;
      }
    },

    async bootstrap() {
      const tenantStore = useTenantStore();
      await tenantStore.fetchAllTenants();
      this.isReady = true;
    },

    async submitToken() {
      const token = this.tokenInput.trim();
      if (!token) {
        this.authError = "Enter a bearer token.";
        return;
      }
      setStoredToken(token);
      this.authError = "";
      try {
        const response = await httpRequest("/ui/tenants?page=1&size=1");
        if (!response.ok) {
          const text = await response.text();
          throw new ApiError(text || "Admin token rejected.", response.status, text);
        }
        this.showAuthPrompt = false;
        this.sessionValidated = true;
        await this.bootstrap();
        await loadRouteData(router.currentRoute.value);
      } catch (err) {
        setStoredToken("");
        this.authError =
          err instanceof ApiError
            ? err.message
            : "Admin token rejected. Use the token from your local .env.local.";
        this.showAuthPrompt = true;
        this.sessionValidated = false;
      }
    },

    logout() {
      setStoredToken("");
      this.tokenInput = "";
      this.showAuthPrompt = true;
      this.isReady = false;
      this.sessionValidated = false;
      router.push({ name: "overview" }).catch(() => undefined);
    },

    handleApiError(err: unknown) {
      const ui = useUiStore();
      if (err instanceof ApiError && err.isUnauthorized) {
        this.logout();
        ui.notify("Session expired. Sign in again.", true);
        return;
      }
      const message = err instanceof Error ? err.message : "Unexpected error";
      ui.notify(message, true);
    },
  },
});
