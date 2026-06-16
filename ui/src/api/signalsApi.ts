import { buildQuery, httpJson } from "@/api/httpClient";
import type { Paginated, Signal } from "@/api/types";

export type SignalListParams = {
  page: number;
  size: number;
  tenant_id?: string;
  checkpoint_id?: string;
  active_only?: boolean;
};

export const signalsApi = {
  list(params: SignalListParams) {
    return httpJson<Paginated<Signal>>(`/ui/signals${buildQuery(params)}`);
  },
  search(params: SignalListParams & { q: string }) {
    return httpJson<Paginated<Signal>>(`/ui/search_signals${buildQuery(params)}`);
  },
  get(id: string) {
    return httpJson<Signal>(`/ui/signals/${id}`);
  },
  create(payload: Record<string, unknown>) {
    return httpJson<Signal>("/ui/signals", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  },
  makeCurrent(id: string) {
    return httpJson<unknown>(`/ui/signals/${id}/make_current`, {
      method: "POST",
    });
  },
};
