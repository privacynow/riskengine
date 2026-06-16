import { defineStore } from "pinia";
import { auditApi } from "@/api/decisionsApi";
import { tenantsApi } from "@/api/tenantsApi";
import { checkpointsApi } from "@/api/checkpointsApi";
import { signalsApi } from "@/api/signalsApi";
import type { DecisionSummary, SignalLogSummary } from "@/api/types";
import { useAuthStore } from "@/stores/authStore";
import { useTenantStore } from "@/stores/tenantStore";

export const useOverviewStore = defineStore("overview", {
  state: () => ({
    loading: false,
    error: "",
    tenantCount: 0,
    checkpointCount: 0,
    signalCount: 0,
    recentDecisionCount: 0,
    failedSignalCount: 0,
    recentDecisions: [] as DecisionSummary[],
    failedSignalLogs: [] as SignalLogSummary[],
  }),
  getters: {
    failureRateLabel(): string {
      if (!this.recentDecisionCount) return "—";
      const rate = Math.round((this.failedSignalCount / Math.max(this.recentDecisionCount, 1)) * 100);
      return `${rate}%`;
    },
  },
  actions: {
    async load() {
      const tenantStore = useTenantStore();
      const tenantId = tenantStore.activeTenantId;
      this.loading = true;
      this.error = "";
      try {
        const decisionParams: Record<string, string | number> = { page: 1, size: 8 };
        const logParams: Record<string, string | number | boolean> = {
          page: 1,
          size: 8,
          failures_only: true,
        };
        if (tenantId) {
          decisionParams.tenant_id = tenantId;
          logParams.tenant_id = tenantId;
        }

        const [tenants, checkpoints, signals, decisions, logs] = await Promise.all([
          tenantsApi.list(1, 1),
          tenantId
            ? checkpointsApi.list({
                page: 1,
                size: 1,
                tenant_id: tenantId,
                active_only: true,
              })
            : Promise.resolve({ total: 0, items: [] }),
          tenantId
            ? signalsApi.list({
                page: 1,
                size: 1,
                tenant_id: tenantId,
                active_only: true,
              })
            : Promise.resolve({ total: 0, items: [] }),
          auditApi.searchDecisions(decisionParams),
          tenantId
            ? auditApi.searchSignalLogs(logParams)
            : Promise.resolve({ items: [], total: 0 }),
        ]);
        this.tenantCount = tenants.total;
        this.checkpointCount = checkpoints.total;
        this.signalCount = signals.total;
        this.recentDecisions = decisions.items;
        this.recentDecisionCount = decisions.total;
        this.failedSignalLogs = logs.items;
        this.failedSignalCount = logs.total;
      } catch (err) {
        useAuthStore().handleApiError(err);
        this.error = err instanceof Error ? err.message : "Failed to load dashboard";
      } finally {
        this.loading = false;
      }
    },
  },
});
