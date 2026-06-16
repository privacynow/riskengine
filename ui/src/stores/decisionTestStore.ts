import { defineStore } from "pinia";
import type { LocationQuery } from "vue-router";
import { checkpointsApi } from "@/api/checkpointsApi";
import { decisionsApi } from "@/api/decisionsApi";
import { signalsApi } from "@/api/signalsApi";
import type { Checkpoint, Signal } from "@/api/types";
import { DEFAULT_PAGE_SIZE } from "@/app/config";
import { requireTenantId } from "@/app/tenantScope";
import { totalPages } from "@/api/types";
import { useAuthStore } from "@/stores/authStore";
import { useUiStore } from "@/stores/uiStore";

export const useDecisionTestStore = defineStore("decisionTest", {
  state: () => ({
    searchTerm: "",
    checkpoints: [] as Checkpoint[],
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    totalPages: 1,
    expanded: {} as Record<string, boolean>,
    applicantIds: {} as Record<string, string>,
    correlationIds: {} as Record<string, string>,
    assocSignals: {} as Record<string, Signal[]>,
    expandedSignals: {} as Record<string, Record<string, boolean>>,
    params: {} as Record<string, Record<string, Record<string, string>>>,
    responses: {} as Record<string, Record<string, unknown>>,
    selectedCheckpointId: null as string | null,
    running: false,
    loading: false,
  }),
  actions: {
    reset() {
      this.checkpoints = [];
      this.page = 1;
      this.totalPages = 1;
      this.expanded = {};
      this.applicantIds = {};
      this.correlationIds = {};
      this.assocSignals = {};
      this.expandedSignals = {};
      this.params = {};
      this.responses = {};
      this.selectedCheckpointId = null;
      this.running = false;
    },

    async selectCheckpoint(id: string) {
      this.selectedCheckpointId = id;
      const existing = this.checkpoints.find((c) => c.id === id);
      if (!existing) {
        const tenantId = requireTenantId();
        if (tenantId) {
          try {
            const cp = await checkpointsApi.get(id);
            if (!this.checkpoints.some((c) => c.id === id)) {
              this.checkpoints = [cp, ...this.checkpoints];
            }
          } catch (err) {
            useAuthStore().handleApiError(err);
          }
        }
      }
      await this.loadSignals(id);
    },

    queryValue(query: LocationQuery, key: string): string {
      const raw = query[key];
      return typeof raw === "string" ? raw : "";
    },

    async applyScenarioFromRoute(query: LocationQuery) {
      const checkpointId = this.queryValue(query, "checkpoint");
      const applicantId = this.queryValue(query, "applicant");
      const correlationId = this.queryValue(query, "correlation");
      const fromDecision = this.queryValue(query, "from_decision");

      if (!checkpointId && !fromDecision) return;

      if (checkpointId) {
        await this.selectCheckpoint(checkpointId);
      }

      const cpId = this.selectedCheckpointId;
      if (!cpId) return;

      if (applicantId) this.applicantIds[cpId] = applicantId;
      if (correlationId) this.correlationIds[cpId] = correlationId;

      if (!fromDecision) return;

      try {
        const detail = await decisionsApi.get(fromDecision);
        if (detail.applicant_id && !applicantId) {
          this.applicantIds[cpId] = detail.applicant_id;
        }
        if (detail.correlation_id && !correlationId) {
          this.correlationIds[cpId] = detail.correlation_id;
        }
        if (detail.checkpoint_id && !checkpointId) {
          await this.selectCheckpoint(detail.checkpoint_id);
        }

        const activeId = this.selectedCheckpointId;
        if (!activeId) return;

        await this.loadSignals(activeId);
        for (const sig of detail.signals ?? []) {
          const signalId = sig.signal_id;
          if (!signalId || !this.params[activeId]?.[signalId]) continue;
          const paramValues = sig.param_values ?? {};
          for (const [placeholder, value] of Object.entries(paramValues)) {
            if (
              placeholder in this.params[activeId][signalId] &&
              value != null &&
              value !== "" &&
              value !== "[REDACTED]"
            ) {
              this.params[activeId][signalId][placeholder] = String(value);
            }
          }
        }
        this.expanded[activeId] = true;
      } catch (err) {
        useAuthStore().handleApiError(err);
      }
    },

    async loadAll(page = 1) {
      const tenantId = requireTenantId();
      if (!tenantId) {
        this.reset();
        return;
      }
      this.page = page;
      this.loading = true;
      try {
        const data = await checkpointsApi.list({
          page,
          size: this.pageSize,
          tenant_id: tenantId,
        });
        this.checkpoints = data.items;
        this.totalPages = totalPages(data.total, this.pageSize);
        this.expanded = {};
      } catch (err) {
        useAuthStore().handleApiError(err);
      } finally {
        this.loading = false;
      }
    },

    async search(page = 1) {
      const tenantId = requireTenantId();
      if (!tenantId) {
        this.reset();
        return;
      }
      const q = this.searchTerm.trim();
      if (!q) {
        await this.loadAll(page);
        return;
      }
      this.page = page;
      try {
        const data = await checkpointsApi.search({
          q,
          page,
          size: this.pageSize,
          tenant_id: tenantId,
        });
        this.checkpoints = data.items;
        this.totalPages = totalPages(data.total, this.pageSize);
        this.expanded = {};
      } catch (err) {
        useAuthStore().handleApiError(err);
      }
    },

    async toggleExpand(checkpointId: string) {
      this.expanded[checkpointId] = !this.expanded[checkpointId];
      if (this.expanded[checkpointId]) await this.loadSignals(checkpointId);
    },

    async loadSignals(checkpointId: string) {
      const tenantId = requireTenantId();
      if (!tenantId) return;
      try {
        const items = await signalsApi.listAll({
          tenant_id: tenantId,
          checkpoint_id: checkpointId,
        });
        this.assocSignals[checkpointId] = items;
        if (!this.expandedSignals[checkpointId]) this.expandedSignals[checkpointId] = {};
        if (!this.params[checkpointId]) this.params[checkpointId] = {};
        for (const sig of items) {
          this.expandedSignals[checkpointId][sig.id] = false;
          if (!this.params[checkpointId][sig.id]) {
            this.params[checkpointId][sig.id] = {};
            for (const ph of sig.param_placeholders || []) {
              this.params[checkpointId][sig.id][ph] = "";
            }
          }
        }
      } catch (err) {
        useAuthStore().handleApiError(err);
      }
    },

    toggleExpandSignal(checkpointId: string, signalId: string) {
      if (!this.expandedSignals[checkpointId]) this.expandedSignals[checkpointId] = {};
      this.expandedSignals[checkpointId][signalId] =
        !this.expandedSignals[checkpointId][signalId];
    },

    async invoke(checkpointId: string) {
      const cp = this.checkpoints.find((c) => c.id === checkpointId);
      if (!cp) {
        useUiStore().notify("Checkpoint not found.", true);
        return;
      }
      const paramMap: Record<string, string> = {};
      const signalParams = this.params[checkpointId] || {};
      for (const placeholders of Object.values(signalParams)) {
        for (const [ph, value] of Object.entries(placeholders)) {
          paramMap[ph] = value;
        }
      }
      this.running = true;
      try {
        const resp = await decisionsApi.test({
          tenant_id: cp.tenant_id,
          checkpoint_name: cp.name,
          checkpoint_id: cp.id,
          applicant_id: this.applicantIds[checkpointId] || undefined,
          correlation_id: this.correlationIds[checkpointId] || undefined,
          parameters: paramMap,
        });
        this.responses[checkpointId] = resp;
      } catch (err) {
        const message = err instanceof Error ? err.message : "Decision failed";
        this.responses[checkpointId] = { error: message };
        useAuthStore().handleApiError(err);
      } finally {
        this.running = false;
      }
    },
  },
});
