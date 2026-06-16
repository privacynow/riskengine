import { defineStore } from "pinia";
import { auditApi, decisionsApi } from "@/api/decisionsApi";
import type {
  DecisionDetail,
  DecisionSummary,
  PromotionAuditSummary,
  SignalLogSummary,
} from "@/api/types";
import { DEFAULT_PAGE_SIZE } from "@/app/config";
import { requireTenantId } from "@/app/tenantScope";
import { totalPages } from "@/api/types";
import { useAuthStore } from "@/stores/authStore";

export type AuditEntityType = "decisions" | "signal_logs" | "promotions";

export const useAuditStore = defineStore("audit", {
  state: () => ({
    entityType: "decisions" as AuditEntityType,
    query: "",
    correlationId: "",
    applicantId: "",
    failuresOnly: false,
    decisions: [] as DecisionSummary[],
    signalLogs: [] as SignalLogSummary[],
    promotions: [] as PromotionAuditSummary[],
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    total: 0,
    totalPages: 1,
    loading: false,
    error: "",
    fromDate: "",
    toDate: "",
    selectedDecisionId: null as string | null,
    selectedSignalLogId: null as string | null,
    selectedPromotionId: null as string | null,
    decisionDetail: null as DecisionDetail | null,
    promotionDetail: null as PromotionAuditSummary | null,
    detailLoading: false,
  }),
  getters: {
    selectedDecision(state): DecisionSummary | undefined {
      return state.decisions.find((d) => d.id === state.selectedDecisionId);
    },
    selectedSignalLog(state): SignalLogSummary | undefined {
      return state.signalLogs.find((l) => l.id === state.selectedSignalLogId);
    },
    selectedPromotion(state): PromotionAuditSummary | undefined {
      if (state.promotionDetail?.id === state.selectedPromotionId) {
        return state.promotionDetail;
      }
      return state.promotions.find((p) => p.id === state.selectedPromotionId);
    },
  },
  actions: {
    buildSearchQuery(): string {
      const parts = [this.query.trim(), this.correlationId.trim(), this.applicantId.trim()].filter(
        Boolean
      );
      return parts.join(" ");
    },

    async search(page = 1) {
      const tenantId = requireTenantId();
      this.page = page;
      this.loading = true;
      this.error = "";
      const q = this.buildSearchQuery();
      try {
        if (this.entityType === "decisions") {
          const params: Record<string, string | number | boolean> = {
            page,
            size: this.pageSize,
          };
          if (q) params.q = q;
          if (this.fromDate) params.from_date = this.fromDate;
          if (this.toDate) params.to_date = this.toDate;
          if (tenantId) params.tenant_id = tenantId;
          const data = await auditApi.searchDecisions(params);
          this.decisions = data.items;
          this.total = data.total;
          this.totalPages = totalPages(data.total, this.pageSize);
        } else if (this.entityType === "signal_logs") {
          const params: Record<string, string | number | boolean> = {
            page,
            size: this.pageSize,
          };
          if (q) params.q = q;
          if (tenantId) params.tenant_id = tenantId;
          if (this.failuresOnly) params.failures_only = true;
          const data = await auditApi.searchSignalLogs(params);
          this.signalLogs = data.items;
          this.total = data.total;
          this.totalPages = totalPages(data.total, this.pageSize);
        } else {
          const params: Record<string, string | number | boolean> = {
            page,
            size: this.pageSize,
          };
          if (q) params.q = q;
          if (tenantId) params.tenant_id = tenantId;
          const data = await auditApi.searchPromotions(params);
          this.promotions = data.items;
          this.total = data.total;
          this.totalPages = totalPages(data.total, this.pageSize);
        }
      } catch (err) {
        useAuthStore().handleApiError(err);
        this.error = err instanceof Error ? err.message : "Search failed";
      } finally {
        this.loading = false;
      }
    },

    async selectDecision(id: string | null) {
      this.selectedDecisionId = id;
      this.selectedSignalLogId = null;
      this.selectedPromotionId = null;
      this.decisionDetail = null;
      if (!id) return;
      this.detailLoading = true;
      try {
        this.decisionDetail = await decisionsApi.get(id);
      } catch (err) {
        useAuthStore().handleApiError(err);
      } finally {
        this.detailLoading = false;
      }
    },

    selectSignalLog(id: string | null) {
      this.selectedSignalLogId = id;
      this.selectedDecisionId = null;
      this.selectedPromotionId = null;
      this.decisionDetail = null;
    },

    async selectPromotion(id: string | null) {
      this.selectedPromotionId = id;
      this.selectedDecisionId = null;
      this.selectedSignalLogId = null;
      this.decisionDetail = null;
      this.promotionDetail = null;
      if (!id) return;
      await this.loadPromotionDetail(id);
    },

    async loadPromotionDetail(id: string) {
      const tenantId = requireTenantId();
      this.detailLoading = true;
      try {
        this.promotionDetail = await auditApi.getPromotion(id, tenantId ?? undefined);
      } catch (err) {
        useAuthStore().handleApiError(err);
        this.promotionDetail = null;
      } finally {
        this.detailLoading = false;
      }
    },

    closeDetail() {
      this.selectedDecisionId = null;
      this.selectedSignalLogId = null;
      this.selectedPromotionId = null;
      this.decisionDetail = null;
      this.promotionDetail = null;
    },
  },
});
