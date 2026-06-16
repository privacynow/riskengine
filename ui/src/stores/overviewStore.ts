import { defineStore } from "pinia";
import { auditApi } from "@/api/decisionsApi";
import { tenantsApi } from "@/api/tenantsApi";
import { checkpointsApi } from "@/api/checkpointsApi";
import { signalsApi } from "@/api/signalsApi";
import type { DecisionSummary, SignalLogSummary } from "@/api/types";
import { useAuthStore } from "@/stores/authStore";
import { useTenantStore } from "@/stores/tenantStore";

const DECISION_SAMPLE_SIZE = 8;
const FLOW_CAP_SAMPLE_SIZE = 50;

function formatCost(value: number): string {
  if (!value) return "—";
  return value.toFixed(2);
}

export const useOverviewStore = defineStore("overview", {
  state: () => ({
    loading: false,
    error: "",
    tenantCount: 0,
    checkpointCount: 0,
    signalCount: 0,
    inactiveCheckpointCount: 0,
    inactiveSignalCount: 0,
    decisionSearchTotal: 0,
    failedSignalCount: 0,
    peakDecisionCost: 0,
    maxFlowCostCap: 0,
    avgDecisionCost: 0,
    recentDecisions: [] as DecisionSummary[],
    failedSignalLogs: [] as SignalLogSummary[],
  }),
  getters: {
    recentSampleCount(): number {
      return this.recentDecisions.length;
    },
    recentSampleHint(): string {
      return `${this.decisionSearchTotal} total in tenant search (not time-bounded)`;
    },
    failedSignalCallsHint(): string {
      return `${this.failedSignalCount} in scoped failure search`;
    },
    staleVersionLabel(): string {
      const total = this.inactiveCheckpointCount + this.inactiveSignalCount;
      return String(total);
    },
    costPressureHint(): string {
      if (!this.maxFlowCostCap) {
        return `No caps in first ${FLOW_CAP_SAMPLE_SIZE} active checkpoints`;
      }
      const pct = Math.round((this.peakDecisionCost / this.maxFlowCostCap) * 100);
      return `${pct}% of sample cap (first ${FLOW_CAP_SAMPLE_SIZE} checkpoints)`;
    },
    peakCostLabel(): string {
      return formatCost(this.peakDecisionCost);
    },
    avgCostLabel(): string {
      return formatCost(this.avgDecisionCost);
    },
    costPressureTone(): "default" | "warning" | "danger" {
      if (!this.maxFlowCostCap || !this.peakDecisionCost) return "default";
      const ratio = this.peakDecisionCost / this.maxFlowCostCap;
      if (ratio >= 0.9) return "danger";
      if (ratio >= 0.7) return "warning";
      return "default";
    },
  },
  actions: {
    async load() {
      const tenantStore = useTenantStore();
      const tenantId = tenantStore.activeTenantId;
      this.loading = true;
      this.error = "";
      try {
        const decisionParams: Record<string, string | number> = {
          page: 1,
          size: DECISION_SAMPLE_SIZE,
        };
        const logParams: Record<string, string | number | boolean> = {
          page: 1,
          size: DECISION_SAMPLE_SIZE,
          failures_only: true,
        };
        if (tenantId) {
          decisionParams.tenant_id = tenantId;
          logParams.tenant_id = tenantId;
        }

        const [
          tenants,
          checkpointsAll,
          checkpointsActive,
          signalsAll,
          signalsActive,
          checkpointSample,
          decisions,
          logs,
        ] = await Promise.all([
          tenantsApi.list(1, 1),
          tenantId
            ? checkpointsApi.list({
                page: 1,
                size: 1,
                tenant_id: tenantId,
              })
            : Promise.resolve({ total: 0, items: [] }),
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
          tenantId
            ? checkpointsApi.list({
                page: 1,
                size: FLOW_CAP_SAMPLE_SIZE,
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
        this.checkpointCount = checkpointsActive.total;
        this.signalCount = signalsActive.total;
        this.inactiveCheckpointCount = Math.max(
          0,
          checkpointsAll.total - checkpointsActive.total
        );
        this.inactiveSignalCount = Math.max(0, signalsAll.total - signalsActive.total);
        this.recentDecisions = decisions.items;
        this.decisionSearchTotal = decisions.total;
        this.failedSignalLogs = logs.items;
        this.failedSignalCount = logs.total;

        const costs = decisions.items
          .map((d) => d.cost_incurred ?? 0)
          .filter((c) => c > 0);
        this.peakDecisionCost = costs.length ? Math.max(...costs) : 0;
        this.avgDecisionCost = costs.length
          ? costs.reduce((sum, c) => sum + c, 0) / costs.length
          : 0;
        this.maxFlowCostCap = checkpointSample.items.reduce(
          (max, cp) => Math.max(max, cp.max_cost ?? 0),
          0
        );
      } catch (err) {
        useAuthStore().handleApiError(err);
        this.error = err instanceof Error ? err.message : "Failed to load dashboard";
      } finally {
        this.loading = false;
      }
    },
  },
});
