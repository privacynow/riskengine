import { defineStore } from "pinia";
import { associationsApi } from "@/api/associationsApi";
import { checkpointsApi } from "@/api/checkpointsApi";
import { signalsApi } from "@/api/signalsApi";
import { DEFAULT_PAGE_SIZE } from "@/app/config";
import { requireTenantId } from "@/app/tenantScope";
import {
  checkpointToDraft,
  emptyCheckpointDraft,
  totalPages,
  type Checkpoint,
  type CheckpointDraft,
} from "@/api/types";
import { useAuthStore } from "@/stores/authStore";
import { useUiStore } from "@/stores/uiStore";
import { useConfirmDialog } from "@/composables/useConfirmDialog";
import { usePromoteDialog } from "@/composables/usePromoteDialog";

export const useCheckpointStore = defineStore("checkpoint", {
  state: () => ({
    activeFilter: "all" as "all" | "active",
    searchTerm: "",
    showCreateForm: false,
    draft: emptyCheckpointDraft(),
    items: [] as Checkpoint[],
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    total: 0,
    totalPages: 1,
    loading: false,
    error: "",
    expanded: {} as Record<string, boolean>,
    edits: {} as Record<string, CheckpointDraft>,
    signalSearch: {} as Record<string, string>,
    signalCandidates: {} as Record<string, { id: string; name: string }[]>,
    signalCandidatePage: {} as Record<string, number>,
    signalCandidateTotalPages: {} as Record<string, number>,
    expandedCandidate: {} as Record<string, Record<string, boolean>>,
    selectedId: null as string | null,
    detailTab: "summary" as "summary" | "config" | "versions" | "signals" | "dsl" | "runtime",
    detailDraft: emptyCheckpointDraft(),
    detailCheckpoint: null as Checkpoint | null,
    versionHistory: [] as Checkpoint[],
    versionHistoryLoading: false,
  }),
  getters: {
    selectedCheckpoint(state): Checkpoint | undefined {
      if (state.detailCheckpoint && state.selectedId === state.detailCheckpoint.id) {
        return state.detailCheckpoint;
      }
      return (
        state.items.find((c) => c.id === state.selectedId) ??
        state.detailCheckpoint ??
        undefined
      );
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
      this.detailDraft = emptyCheckpointDraft();
      this.detailCheckpoint = null;
    },

    closeDetail() {
      void this.selectCheckpoint(null);
    },

    async selectCheckpoint(id: string | null) {
      this.selectedId = id;
      if (!id) {
        this.detailDraft = emptyCheckpointDraft();
        this.detailCheckpoint = null;
        return;
      }
      const fromList = this.items.find((c) => c.id === id);
      if (fromList) {
        this.detailCheckpoint = fromList;
        this.detailDraft = checkpointToDraft(fromList);
        await this.loadDetailAssociations(id);
        void this.loadVersionHistory(id);
        return;
      }
      await this.loadCheckpointDetail(id);
    },

    async loadVersionHistory(checkpointId: string) {
      this.versionHistoryLoading = true;
      try {
        const data = await checkpointsApi.listVersions(checkpointId);
        this.versionHistory = data.items;
      } catch (err) {
        useAuthStore().handleApiError(err);
        this.versionHistory = [];
      } finally {
        this.versionHistoryLoading = false;
      }
    },

    async loadCheckpointDetail(id: string) {
      try {
        const cp = await checkpointsApi.get(id);
        this.detailCheckpoint = cp;
        this.detailDraft = checkpointToDraft(cp);
        if (!this.items.some((c) => c.id === id)) {
          this.items = [cp, ...this.items];
        }
        await this.loadDetailAssociations(id);
        void this.loadVersionHistory(id);
      } catch (err) {
        this.detailCheckpoint = null;
        useAuthStore().handleApiError(err);
      }
    },

    async loadDetailAssociations(checkpointId: string) {
      const tenantId = requireTenantId();
      if (!tenantId) return;
      try {
        const items = await signalsApi.listAll({
          tenant_id: tenantId,
          checkpoint_id: checkpointId,
        });
        if (this.selectedId === checkpointId) {
          this.detailDraft.associatedSignals = items;
        }
        if (this.edits[checkpointId]) {
          this.edits[checkpointId].associatedSignals = items;
        }
      } catch (err) {
        useAuthStore().handleApiError(err);
      }
    },

    ensureEdit(cp: Checkpoint) {
      if (!this.edits[cp.id]) {
        this.edits[cp.id] = checkpointToDraft(cp);
      }
    },

    async loadAll(page = 1) {
      const tenantId = requireTenantId();
      if (!tenantId) {
        this.clearListState();
        return;
      }
      this.searchTerm = "";
      this.page = page;
      this.loading = true;
      try {
        const data = await checkpointsApi.list({
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
        const data = await checkpointsApi.search({
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
      if (this.showCreateForm) this.draft = emptyCheckpointDraft();
    },

    draftToCreatePayload(draft: CheckpointDraft, tenantId: string, copyFromCheckpointId?: string): Record<string, unknown> {
      const payload: Record<string, unknown> = {
        tenant_id: tenantId,
        name: draft.name,
        description: draft.description,
        type: draft.type,
        dsl_expression: draft.dsl_expression,
        method_of_call: draft.method_of_call,
        max_cost: draft.max_cost,
        override_cost_flag: draft.override_cost_flag,
        timeout_seconds: draft.timeout_seconds,
        signals: draft.associatedSignals.map((s) => s.id),
      };
      if (copyFromCheckpointId) {
        payload.copyFromCheckpointId = copyFromCheckpointId;
      }
      return payload;
    },

    draftToMetadataPayload(draft: CheckpointDraft): Record<string, unknown> {
      return {
        description: draft.description,
      };
    },

    async create(force = false) {
      const tenantId = requireTenantId();
      if (!tenantId) {
        useUiStore().notify("Please select a tenant first.", true);
        return;
      }
      if (!this.draft.name || !this.draft.type || !this.draft.dsl_expression) {
        useUiStore().notify("Name, type, and DSL expression are required.", true);
        return;
      }
      if (!force) {
        try {
          const existing = await checkpointsApi.search({
            q: this.draft.name,
            page: 1,
            size: 1,
            tenant_id: tenantId,
          });
          const match = existing.items.find((cp) => cp.name === this.draft.name);
          if (match) {
            const { confirm } = useConfirmDialog();
            const ok = await confirm({
              title: "Create new checkpoint version?",
              message: `A checkpoint named "${this.draft.name}" already exists. Create a new version?`,
              confirmLabel: "Create version",
            });
            if (!ok) return;
          }
        } catch (err) {
          useAuthStore().handleApiError(err);
          return;
        }
      }
      try {
        await checkpointsApi.create(
          this.draftToCreatePayload(this.draft, tenantId)
        );
        this.draft = emptyCheckpointDraft();
        this.showCreateForm = false;
        await this.loadAll(this.page);
        useUiStore().notify("Checkpoint created.");
      } catch (err) {
        useAuthStore().handleApiError(err);
      }
    },

    toggleExpand(id: string) {
      this.expanded[id] = !this.expanded[id];
      if (!this.expanded[id]) return;
      const cp = this.items.find((c) => c.id === id);
      if (cp) {
        this.ensureEdit(cp);
        void this.loadAssociations(id);
      }
    },

    async saveDetail(): Promise<string | undefined> {
      const cp = this.selectedCheckpoint;
      if (!cp) return;
      try {
        const created = await checkpointsApi.create(
          this.draftToCreatePayload(this.detailDraft, cp.tenant_id, cp.id)
        );
        const newId = String((created as { id: string }).id);
        await this.loadAll(this.page);
        await this.selectCheckpoint(newId);
        useUiStore().notify("Checkpoint version saved.");
        return newId;
      } catch (err) {
        useAuthStore().handleApiError(err);
      }
    },

    async saveMetadata(id: string) {
      const edit = this.edits[id];
      if (!edit) return;
      try {
        await checkpointsApi.update(id, this.draftToMetadataPayload(edit));
        this.expanded[id] = false;
        await this.loadAll(this.page);
        useUiStore().notify("Description updated.");
      } catch (err) {
        useAuthStore().handleApiError(err);
      }
    },

    async save(id: string) {
      const edit = this.edits[id];
      const cp = this.items.find((c) => c.id === id);
      if (!edit || !cp) return;
      try {
        const created = await checkpointsApi.create(
          this.draftToCreatePayload(edit, cp.tenant_id, id)
        );
        this.expanded[id] = false;
        await this.loadAll(this.page);
        const newId = String((created as { id: string }).id);
        await this.selectCheckpoint(newId);
        useUiStore().notify("Checkpoint version saved.");
      } catch (err) {
        useAuthStore().handleApiError(err);
      }
    },

    async loadAssociations(checkpointId: string) {
      await this.loadDetailAssociations(checkpointId);
    },

    async removeAssociation(checkpointId: string, signalId: string) {
      const tenantId = requireTenantId();
      if (!tenantId) return;
      try {
        const assoc = await associationsApi.list({
          tenant_id: tenantId,
          checkpoint_id: checkpointId,
          signal_id: signalId,
          size: 1,
        });
        const row = assoc.items[0];
        if (!row) {
          useUiStore().notify("Association not found.", true);
          return;
        }
        await associationsApi.remove(row.id);
        await this.loadAssociations(checkpointId);
      } catch (err) {
        useAuthStore().handleApiError(err);
      }
    },

    async setCurrentVersion(checkpointId: string) {
      const cp = this.selectedCheckpoint ?? this.items.find((c) => c.id === checkpointId);
      if (!cp || cp.id !== checkpointId) return;
      const { promote } = usePromoteDialog();
      const reason = await promote({
        title: "Promote checkpoint version",
        message: `Promote "${cp.name}" to the live current version for this tenant.`,
        confirmLabel: "Promote",
      });
      if (!reason) return;
      try {
        await checkpointsApi.makeCurrent(checkpointId, {
          promotionReason: reason,
        });
        await this.loadAll(this.page);
        if (this.selectedId === checkpointId) {
          await this.selectCheckpoint(checkpointId);
        } else {
          void this.loadVersionHistory(checkpointId);
        }
        useUiStore().notify("Current checkpoint version updated.");
      } catch (err) {
        useAuthStore().handleApiError(err);
      }
    },

    async deactivateVersion(checkpointId: string) {
      const cp = this.selectedCheckpoint ?? this.items.find((c) => c.id === checkpointId);
      if (!cp || cp.id !== checkpointId || !cp.is_current_version) return;
      const { promote } = usePromoteDialog();
      const reason = await promote({
        title: "Deactivate checkpoint",
        message: `Remove "${cp.name}" from live runtime. Decisions by name will fail until another version is promoted or reactivated.`,
        confirmLabel: "Deactivate",
        reasonPlaceholder: "Why is this checkpoint being deactivated?",
      });
      if (!reason) return;
      try {
        await checkpointsApi.deactivate(checkpointId, { promotionReason: reason });
        await this.loadAll(this.page);
        if (this.selectedId === checkpointId) {
          await this.selectCheckpoint(checkpointId);
        } else {
          void this.loadVersionHistory(checkpointId);
        }
        useUiStore().notify("Checkpoint deactivated.");
      } catch (err) {
        useAuthStore().handleApiError(err);
      }
    },

    async reactivateVersion(checkpointId: string) {
      const cp = this.selectedCheckpoint ?? this.items.find((c) => c.id === checkpointId);
      if (
        !cp ||
        cp.id !== checkpointId ||
        cp.is_current_version ||
        cp.name_has_current_version !== false
      ) {
        return;
      }
      const { promote } = usePromoteDialog();
      const reason = await promote({
        title: "Reactivate checkpoint",
        message: `Restore "${cp.name}" as the live current version for this tenant.`,
        confirmLabel: "Reactivate",
        reasonPlaceholder: "Why is this checkpoint being reactivated?",
      });
      if (!reason) return;
      try {
        await checkpointsApi.reactivate(checkpointId, { promotionReason: reason });
        await this.loadAll(this.page);
        if (this.selectedId === checkpointId) {
          await this.selectCheckpoint(checkpointId);
        } else {
          void this.loadVersionHistory(checkpointId);
        }
        useUiStore().notify("Checkpoint reactivated.");
      } catch (err) {
        useAuthStore().handleApiError(err);
      }
    },

    async loadDraftSignals(page: number) {
      const tenantId = requireTenantId();
      if (!tenantId) {
        this.draft.signalSearchResults = [];
        return;
      }
      const q = this.draft.signalSearch.trim();
      try {
        const data = q
          ? await signalsApi.search({
              q,
              page,
              size: this.draft.signalSize,
              tenant_id: tenantId,
            })
          : await signalsApi.list({
              page,
              size: this.draft.signalSize,
              tenant_id: tenantId,
            });
        this.draft.signalSearchResults = data.items;
        this.draft.signalPage = page;
        this.draft.signalTotalPages = totalPages(data.total, this.draft.signalSize);
      } catch (err) {
        useAuthStore().handleApiError(err);
      }
    },

    addSignalToDraft(signalId: string) {
      const signal = this.draft.signalSearchResults.find((s) => s.id === signalId);
      if (signal && !this.draft.associatedSignals.some((s) => s.id === signalId)) {
        this.draft.associatedSignals.push(signal);
      }
    },

    removeSignalFromDraft(signalId: string) {
      this.draft.associatedSignals = this.draft.associatedSignals.filter(
        (s) => s.id !== signalId
      );
    },

    async associateSignal(checkpointId: string, signalId: string) {
      try {
        await associationsApi.create({ checkpoint_id: checkpointId, signal_id: signalId });
        await this.loadAssociations(checkpointId);
      } catch (err) {
        useAuthStore().handleApiError(err);
      }
    },

    async searchSignalsForDetail(page: number) {
      const tenantId = requireTenantId();
      if (!tenantId || !this.selectedId) return;
      const q = this.detailDraft.signalSearch.trim();
      try {
        const data = q
          ? await signalsApi.search({
              q,
              page,
              size: this.detailDraft.signalSize,
              tenant_id: tenantId,
            })
          : await signalsApi.list({
              page,
              size: this.detailDraft.signalSize,
              tenant_id: tenantId,
            });
        this.detailDraft.signalSearchResults = data.items;
        this.detailDraft.signalPage = page;
        this.detailDraft.signalTotalPages = totalPages(data.total, this.detailDraft.signalSize);
      } catch (err) {
        useAuthStore().handleApiError(err);
      }
    },

    addSignalToDetail(signalId: string) {
      const signal = this.detailDraft.signalSearchResults.find((s) => s.id === signalId);
      if (signal && !this.detailDraft.associatedSignals.some((s) => s.id === signalId)) {
        this.detailDraft.associatedSignals.push(signal);
      }
    },

    removeSignalFromDetail(signalId: string) {
      this.detailDraft.associatedSignals = this.detailDraft.associatedSignals.filter(
        (s) => s.id !== signalId
      );
    },

    async persistDetailAssociations() {
      const cp = this.selectedCheckpoint;
      if (!cp) return;
      try {
        const current = await signalsApi.listAll({
          tenant_id: cp.tenant_id,
          checkpoint_id: cp.id,
        });
        const desired = new Set(this.detailDraft.associatedSignals.map((s) => s.id));
        const currentIds = new Set(current.map((s) => s.id));
        for (const sig of this.detailDraft.associatedSignals) {
          if (!currentIds.has(sig.id)) {
            await associationsApi.create({ checkpoint_id: cp.id, signal_id: sig.id });
          }
        }
        for (const sig of current) {
          if (!desired.has(sig.id)) {
            await this.removeAssociation(cp.id, sig.id);
          }
        }
        await this.loadDetailAssociations(cp.id);
        useUiStore().notify("Signal associations updated.");
      } catch (err) {
        useAuthStore().handleApiError(err);
      }
    },

    async searchSignalsForEdit(checkpointId: string, page: number) {
      const tenantId = requireTenantId();
      if (!tenantId) return;
      this.signalCandidatePage[checkpointId] = page;
      const q = (this.signalSearch[checkpointId] || "").trim();
      try {
        const data = q
          ? await signalsApi.search({ q, page, size: 5, tenant_id: tenantId })
          : await signalsApi.list({ page, size: 5, tenant_id: tenantId });
        this.signalCandidates[checkpointId] = data.items.map((s) => ({
          id: s.id,
          name: s.name,
        }));
        this.signalCandidateTotalPages[checkpointId] = totalPages(data.total, 5);
      } catch (err) {
        useAuthStore().handleApiError(err);
      }
    },
  },
});
