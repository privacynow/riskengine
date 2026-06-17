import { defineStore } from "pinia";
import { associationsApi } from "@/api/associationsApi";
import { checkpointsApi } from "@/api/checkpointsApi";
import { signalsApi } from "@/api/signalsApi";
import { DEFAULT_PAGE_SIZE } from "@/app/config";
import { requireTenantId } from "@/app/tenantScope";
import {
  emptySignalDraft,
  signalToDraft,
  totalPages,
  type Signal,
  type SignalDraft,
} from "@/api/types";
import { useAuthStore } from "@/stores/authStore";
import { usePromoteDialog } from "@/composables/usePromoteDialog";
import { useUiStore } from "@/stores/uiStore";

type SignalEdit = {
  name: string;
  description: string;
  method_of_call: string;
  cost: number;
  bearer_token: string;
  associatedCheckpoints: { id: string; name: string }[];
};

export const useSignalStore = defineStore("signal", {
  state: () => ({
    activeFilter: "all" as "all" | "active",
    searchTerm: "",
    showCreateForm: false,
    draft: emptySignalDraft(),
    items: [] as Signal[],
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    total: 0,
    totalPages: 1,
    loading: false,
    error: "",
    expanded: {} as Record<string, boolean>,
    edits: {} as Record<string, SignalEdit>,
    checkpointSearch: {} as Record<string, string>,
    checkpointCandidates: {} as Record<string, { id: string; name: string }[]>,
    checkpointCandidatePage: {} as Record<string, number>,
    checkpointCandidateTotalPages: {} as Record<string, number>,
    expandedCandidate: {} as Record<string, Record<string, boolean>>,
    selectedId: null as string | null,
    detailTab: "summary" as "summary" | "config" | "versions" | "associations" | "variables",
    detailDraft: emptySignalDraft(),
    detailAssociatedCheckpoints: [] as { id: string; name: string }[],
    detailSignal: null as Signal | null,
    versionHistory: [] as Signal[],
    versionHistoryLoading: false,
  }),
  getters: {
    selectedSignal(state): Signal | undefined {
      if (state.detailSignal && state.selectedId === state.detailSignal.id) {
        return state.detailSignal;
      }
      return state.items.find((s) => s.id === state.selectedId) ?? state.detailSignal ?? undefined;
    },
  },
  actions: {
    clearListState() {
      this.items = [];
      this.total = 0;
      this.totalPages = 1;
      this.page = 1;
      this.expanded = {};
      this.edits = {};
      this.selectedId = null;
      this.detailAssociatedCheckpoints = [];
      this.detailSignal = null;
    },

    closeDetail() {
      void this.selectSignal(null);
    },

    async selectSignal(id: string | null) {
      this.selectedId = id;
      if (!id) {
        this.detailDraft = emptySignalDraft();
        this.detailAssociatedCheckpoints = [];
        this.detailSignal = null;
        return;
      }
      const fromList = this.items.find((s) => s.id === id);
      if (fromList) {
        this.detailSignal = fromList;
        this.detailDraft = signalToDraft(fromList);
        void this.loadAssociations(id);
        void this.loadVersionHistory(id);
        return;
      }
      await this.loadSignalDetail(id);
    },

    async loadVersionHistory(signalId: string) {
      this.versionHistoryLoading = true;
      try {
        const data = await signalsApi.listVersions(signalId);
        this.versionHistory = data.items;
      } catch (err) {
        useAuthStore().handleApiError(err);
        this.versionHistory = [];
      } finally {
        this.versionHistoryLoading = false;
      }
    },

    async loadSignalDetail(id: string) {
      try {
        const signal = await signalsApi.get(id);
        this.detailSignal = signal;
        this.detailDraft = signalToDraft(signal);
        if (!this.items.some((s) => s.id === id)) {
          this.items = [signal, ...this.items];
        }
        void this.loadAssociations(id);
        void this.loadVersionHistory(id);
      } catch (err) {
        this.detailSignal = null;
        useAuthStore().handleApiError(err);
      }
    },

    ensureEdit(signal: Signal) {
      if (!this.edits[signal.id]) {
        this.edits[signal.id] = {
          name: signal.name,
          description: signal.description || "",
          method_of_call: signal.method_of_call || "",
          cost: signal.cost || 0,
          bearer_token: "",
          associatedCheckpoints: [],
        };
      }
    },

    async loadAll(page = 1, updateId?: string) {
      const tenantId = requireTenantId();
      if (!tenantId) {
        if (!updateId) this.clearListState();
        return;
      }
      this.page = page;
      this.loading = true;
      this.error = "";
      try {
        const data = await signalsApi.list({
          page,
          size: this.pageSize,
          tenant_id: tenantId,
          active_only: this.activeFilter === "active" ? true : undefined,
        });
        if (updateId) {
          const updated = data.items.find((s) => s.id === updateId);
          const idx = this.items.findIndex((s) => s.id === updateId);
          if (updated && idx >= 0) this.items[idx] = updated;
        } else {
          this.items = data.items;
          this.total = data.total;
          this.totalPages = totalPages(data.total, this.pageSize);
          this.expanded = {};
          this.edits = {};
        }
      } catch (err) {
        useAuthStore().handleApiError(err);
        if (!updateId) this.clearListState();
      } finally {
        this.loading = false;
      }
    },

    async search(page = 1) {
      const tenantId = requireTenantId();
      if (!tenantId) {
        this.clearListState();
        return;
      }
      const q = this.searchTerm.trim();
      if (!q) {
        await this.loadAll(page);
        return;
      }
      this.page = page;
      this.loading = true;
      try {
        const data = await signalsApi.search({
          q,
          page,
          size: this.pageSize,
          tenant_id: tenantId,
          active_only: this.activeFilter === "active" ? true : undefined,
        });
        this.items = data.items;
        this.total = data.total;
        this.totalPages = totalPages(data.total, this.pageSize);
        this.expanded = {};
        this.edits = {};
      } catch (err) {
        useAuthStore().handleApiError(err);
      } finally {
        this.loading = false;
      }
    },

    toggleCreateForm() {
      this.showCreateForm = !this.showCreateForm;
      if (this.showCreateForm) this.draft = emptySignalDraft();
    },

    draftToPayload(draft: SignalDraft, tenantId: string, copyFromSignalId?: string): Record<string, unknown> {
      const payload: Record<string, unknown> = {
        tenant_id: tenantId,
        name: draft.name,
        description: draft.description,
        type: draft.type,
        method_of_call: draft.method_of_call,
        expression_body: draft.expression_body,
        cost: draft.cost,
        cache_expiration_seconds: draft.cache_expiration_seconds,
        timeout_seconds: draft.timeout_seconds,
        can_run_in_parallel: draft.can_run_in_parallel,
        order_of_evaluation: draft.order_of_evaluation,
        http_method: draft.http_method,
        request_url_params_template: draft.request_url_params_template,
        request_body_template: draft.request_body_template,
        request_headers_template: draft.request_headers_template,
        allow_caching: draft.allow_caching,
        global_reuse: draft.global_reuse,
        function_params_template: draft.function_params_template,
      };
      const token = draft.bearer_token.trim();
      if (token) payload.bearer_token = token;
      if (copyFromSignalId) payload.copyFromSignalId = copyFromSignalId;
      return payload;
    },

    async create() {
      const tenantId = requireTenantId();
      if (!tenantId) {
        useUiStore().notify("Please select a tenant first.", true);
        return;
      }
      try {
        await signalsApi.create(this.draftToPayload(this.draft, tenantId));
        this.draft = emptySignalDraft();
        this.showCreateForm = false;
        await this.loadAll(this.page);
        useUiStore().notify("Signal created.");
      } catch (err) {
        useAuthStore().handleApiError(err);
      }
    },

    toggleExpand(id: string) {
      this.expanded[id] = !this.expanded[id];
      if (!this.expanded[id]) return;
      const signal = this.items.find((s) => s.id === id);
      if (signal) {
        this.ensureEdit(signal);
        void this.loadAssociations(id);
      }
    },

    async saveDetail(): Promise<string | undefined> {
      const signal = this.selectedSignal;
      if (!signal) return;
      try {
        const created = await signalsApi.create(
          this.draftToPayload(this.detailDraft, signal.tenant_id, signal.id)
        );
        const newId = String((created as { id: string }).id);
        await this.loadAll(this.page);
        await this.selectSignal(newId);
        useUiStore().notify("Signal version saved.");
        return newId;
      } catch (err) {
        useAuthStore().handleApiError(err);
      }
    },

    async loadAssociations(signalId: string) {
      const tenantId = requireTenantId();
      if (!tenantId) return;
      try {
        const assoc = await associationsApi.listAll({
          tenant_id: tenantId,
          signal_id: signalId,
        });
        if (this.edits[signalId]) {
          this.edits[signalId].associatedCheckpoints = assoc.map((row) => ({
            id: row.checkpoint_id,
            name: row.checkpoint_name || row.checkpoint_id,
          }));
        }
        if (this.selectedId === signalId) {
          this.detailAssociatedCheckpoints = assoc.map((row) => ({
            id: row.checkpoint_id,
            name: row.checkpoint_name || row.checkpoint_id,
          }));
        }
      } catch (err) {
        useAuthStore().handleApiError(err);
      }
    },

    async removeAssociation(signalId: string, checkpointId: string) {
      const tenantId = requireTenantId();
      if (!tenantId) return;
      try {
        const assoc = await associationsApi.list({
          tenant_id: tenantId,
          signal_id: signalId,
          checkpoint_id: checkpointId,
          size: 1,
        });
        const row = assoc.items[0];
        if (!row) {
          useUiStore().notify("Association not found.", true);
          return;
        }
        await associationsApi.remove(row.id);
        await this.loadAssociations(signalId);
      } catch (err) {
        useAuthStore().handleApiError(err);
      }
    },

    async setCurrentVersion(signalId: string) {
      const signal = this.selectedSignal ?? this.items.find((s) => s.id === signalId);
      if (!signal || signal.id !== signalId) return;
      const { promote } = usePromoteDialog();
      const reason = await promote({
        title: "Promote signal version",
        message: `Promote "${signal.name}" to the live current version for this tenant.`,
        confirmLabel: "Promote",
      });
      if (!reason) return;
      try {
        await signalsApi.makeCurrent(signalId, { promotionReason: reason });
        await this.loadAll(this.page);
        if (this.selectedId === signalId) {
          await this.selectSignal(signalId);
        } else {
          void this.loadVersionHistory(signalId);
        }
        useUiStore().notify("Current signal version updated.");
      } catch (err) {
        useAuthStore().handleApiError(err);
      }
    },

    async deactivateVersion(signalId: string) {
      const signal = this.selectedSignal ?? this.items.find((s) => s.id === signalId);
      if (!signal || signal.id !== signalId || !signal.is_current_version) return;
      const { promote } = usePromoteDialog();
      const reason = await promote({
        title: "Deactivate signal",
        message: `Remove "${signal.name}" from live runtime. Linked checkpoints will skip this signal until another version is promoted or reactivated.`,
        confirmLabel: "Deactivate",
        reasonPlaceholder: "Why is this signal being deactivated?",
      });
      if (!reason) return;
      try {
        await signalsApi.deactivate(signalId, { promotionReason: reason });
        await this.loadAll(this.page);
        if (this.selectedId === signalId) {
          await this.selectSignal(signalId);
        } else {
          void this.loadVersionHistory(signalId);
        }
        useUiStore().notify("Signal deactivated.");
      } catch (err) {
        useAuthStore().handleApiError(err);
      }
    },

    async reactivateVersion(signalId: string) {
      const signal = this.selectedSignal ?? this.items.find((s) => s.id === signalId);
      if (
        !signal ||
        signal.id !== signalId ||
        signal.is_current_version ||
        signal.name_has_current_version !== false
      ) {
        return;
      }
      const { promote } = usePromoteDialog();
      const reason = await promote({
        title: "Reactivate signal",
        message: `Restore "${signal.name}" as the live current version for this tenant.`,
        confirmLabel: "Reactivate",
        reasonPlaceholder: "Why is this signal being reactivated?",
      });
      if (!reason) return;
      try {
        await signalsApi.reactivate(signalId, { promotionReason: reason });
        await this.loadAll(this.page);
        if (this.selectedId === signalId) {
          await this.selectSignal(signalId);
        } else {
          void this.loadVersionHistory(signalId);
        }
        useUiStore().notify("Signal reactivated.");
      } catch (err) {
        useAuthStore().handleApiError(err);
      }
    },

    async searchCheckpointsForEdit(signalId: string, page: number) {
      const tenantId = requireTenantId();
      if (!tenantId) return;
      this.checkpointCandidatePage[signalId] = page;
      const q = (this.checkpointSearch[signalId] || "").trim();
      try {
        const data = q
          ? await checkpointsApi.search({ q, page, size: 5, tenant_id: tenantId })
          : await checkpointsApi.list({ page, size: 5, tenant_id: tenantId });
        this.checkpointCandidates[signalId] = data.items.map((cp) => ({
          id: cp.id,
          name: cp.name,
        }));
        this.checkpointCandidateTotalPages[signalId] = totalPages(data.total, 5);
      } catch (err) {
        useAuthStore().handleApiError(err);
      }
    },

    async associateCheckpoint(signalId: string, checkpointId: string) {
      try {
        await associationsApi.create({ checkpoint_id: checkpointId, signal_id: signalId });
        await this.loadAssociations(signalId);
      } catch (err) {
        useAuthStore().handleApiError(err);
      }
    },
  },
});
