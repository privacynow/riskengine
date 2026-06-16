import { buildQuery, httpJson } from "@/api/httpClient";
import type {
  DecisionDetail,
  DecisionSummary,
  DecisionTestPayload,
  DecisionTestResponse,
  Paginated,
  PromotionAuditSummary,
  SignalLogSummary,
} from "@/api/types";

export const decisionsApi = {
  search(params: Record<string, string | number | boolean | undefined>) {
    return httpJson<Paginated<DecisionSummary>>(
      `/ui/search_decisions${buildQuery(params)}`
    );
  },
  get(id: string) {
    return httpJson<DecisionDetail>(`/decisions/${id}`);
  },
  test(payload: DecisionTestPayload) {
    return httpJson<DecisionTestResponse>("/ui/test_decisions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  },
};

export const auditApi = {
  searchDecisions(params: Record<string, string | number | boolean | undefined>) {
    return decisionsApi.search(params);
  },
  searchSignalLogs(params: Record<string, string | number | boolean | undefined>) {
    return httpJson<Paginated<SignalLogSummary>>(
      `/ui/search_signal_logs${buildQuery(params)}`
    );
  },
  searchPromotions(params: Record<string, string | number | boolean | undefined>) {
    return httpJson<Paginated<PromotionAuditSummary>>(
      `/ui/promotion_audit${buildQuery(params)}`
    );
  },
  getPromotion(id: string, tenantId?: string) {
    const params = tenantId ? { tenant_id: tenantId } : undefined;
    return httpJson<PromotionAuditSummary>(
      `/ui/promotion_audit/${encodeURIComponent(id)}${buildQuery(params ?? {})}`
    );
  },
};
