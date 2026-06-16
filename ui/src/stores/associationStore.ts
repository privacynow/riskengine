import { defineStore } from "pinia";
import { associationsApi } from "@/api/associationsApi";
import { checkpointsApi } from "@/api/checkpointsApi";
import { signalsApi } from "@/api/signalsApi";
import { DEFAULT_PAGE_SIZE } from "@/app/config";
import { requireTenantId } from "@/app/tenantScope";
import { totalPages } from "@/api/types";
import { useAuthStore } from "@/stores/authStore";
import { useUiStore } from "@/stores/uiStore";

export const useAssociationStore = defineStore("association", {
  state: () => ({
    mode: "checkpoint" as "checkpoint" | "signal",
    checkpointSearchTerm: "",
    signalSearchTerm: "",
    checkpoints: [] as { id: string; name: string; tenant_id: string }[],
    signals: [] as { id: string; name: string; tenant_id: string }[],
    checkpointPage: 1,
    signalPage: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    checkpointTotalPages: 1,
    signalTotalPages: 1,
    expandedCheckpoint: {} as Record<string, boolean>,
    expandedSignal: {} as Record<string, boolean>,
    checkpointMap: {} as Record<string, { signals: { id: string; name: string }[] }>,
    signalMap: {} as Record<string, { checkpoints: { id: string; name: string }[] }>,
    checkpointSignalSearch: {} as Record<string, string>,
    signalCheckpointSearch: {} as Record<string, string>,
    checkpointCandidates: {} as Record<string, { id: string; name: string }[]>,
    signalCandidates: {} as Record<string, { id: string; name: string }[]>,
    loading: false,
  }),
  actions: {
    reset() {
      this.checkpointSearchTerm = "";
      this.signalSearchTerm = "";
      this.checkpoints = [];
      this.signals = [];
      this.checkpointPage = 1;
      this.signalPage = 1;
      this.checkpointMap = {};
      this.signalMap = {};
      this.expandedCheckpoint = {};
      this.expandedSignal = {};
    },

    async loadCheckpoints(page: number) {
      const tenantId = requireTenantId();
      if (!tenantId) {
        this.checkpoints = [];
        return;
      }
      this.checkpointPage = page;
      this.loading = true;
      try {
        const data = await checkpointsApi.list({
          page,
          size: this.pageSize,
          tenant_id: tenantId,
        });
        this.checkpoints = data.items;
        this.checkpointTotalPages = totalPages(data.total, this.pageSize);
        this.expandedCheckpoint = {};
        this.checkpointMap = {};
      } catch (err) {
        useAuthStore().handleApiError(err);
      } finally {
        this.loading = false;
      }
    },

    async searchCheckpoints(page: number) {
      const tenantId = requireTenantId();
      if (!tenantId) {
        this.checkpoints = [];
        return;
      }
      const q = this.checkpointSearchTerm.trim();
      if (!q) {
        await this.loadCheckpoints(page);
        return;
      }
      this.checkpointPage = page;
      try {
        const data = await checkpointsApi.search({
          q,
          page,
          size: this.pageSize,
          tenant_id: tenantId,
        });
        this.checkpoints = data.items;
        this.checkpointTotalPages = totalPages(data.total, this.pageSize);
        this.expandedCheckpoint = {};
        this.checkpointMap = {};
      } catch (err) {
        useAuthStore().handleApiError(err);
      }
    },

    async loadSignals(page: number) {
      const tenantId = requireTenantId();
      if (!tenantId) {
        this.signals = [];
        return;
      }
      this.signalPage = page;
      try {
        const data = await signalsApi.list({
          page,
          size: this.pageSize,
          tenant_id: tenantId,
        });
        this.signals = data.items;
        this.signalTotalPages = totalPages(data.total, this.pageSize);
        this.expandedSignal = {};
        this.signalMap = {};
      } catch (err) {
        useAuthStore().handleApiError(err);
      }
    },

    async searchSignals(page: number) {
      const tenantId = requireTenantId();
      if (!tenantId) {
        this.signals = [];
        return;
      }
      const q = this.signalSearchTerm.trim();
      if (!q) {
        await this.loadSignals(page);
        return;
      }
      this.signalPage = page;
      try {
        const data = await signalsApi.search({
          q,
          page,
          size: this.pageSize,
          tenant_id: tenantId,
        });
        this.signals = data.items;
        this.signalTotalPages = totalPages(data.total, this.pageSize);
        this.expandedSignal = {};
        this.signalMap = {};
      } catch (err) {
        useAuthStore().handleApiError(err);
      }
    },

    async loadCheckpointMap(checkpointId: string) {
      const tenantId = requireTenantId();
      if (!tenantId) return;
      try {
        const items = await signalsApi.listAll({
          tenant_id: tenantId,
          checkpoint_id: checkpointId,
        });
        this.checkpointMap[checkpointId] = {
          signals: items.map((s) => ({ id: s.id, name: s.name })),
        };
      } catch (err) {
        useAuthStore().handleApiError(err);
      }
    },

    async loadSignalMap(signalId: string) {
      const tenantId = requireTenantId();
      if (!tenantId) return;
      try {
        const assoc = await associationsApi.listAll({
          tenant_id: tenantId,
          signal_id: signalId,
        });
        this.signalMap[signalId] = {
          checkpoints: assoc.map((row) => ({
            id: row.checkpoint_id,
            name: row.checkpoint_name || row.checkpoint_id,
          })),
        };
      } catch (err) {
        useAuthStore().handleApiError(err);
      }
    },

    toggleExpandCheckpoint(id: string) {
      this.expandedCheckpoint[id] = !this.expandedCheckpoint[id];
      if (this.expandedCheckpoint[id]) void this.loadCheckpointMap(id);
    },

    toggleExpandSignal(id: string) {
      this.expandedSignal[id] = !this.expandedSignal[id];
      if (this.expandedSignal[id]) void this.loadSignalMap(id);
    },

    async associate(checkpointId: string, signalId: string) {
      try {
        await associationsApi.create({ checkpoint_id: checkpointId, signal_id: signalId });
        await this.loadCheckpointMap(checkpointId);
        useUiStore().notify("Association created.");
      } catch (err) {
        useAuthStore().handleApiError(err);
      }
    },
  },
});
