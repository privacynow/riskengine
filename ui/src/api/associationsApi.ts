import { buildQuery, httpJson } from "@/api/httpClient";
import type { CheckpointSignal, Paginated } from "@/api/types";

export type AssociationListParams = {
  page?: number;
  size?: number;
  tenant_id?: string;
  checkpoint_id?: string;
  signal_id?: string;
};

export const associationsApi = {
  list(params: AssociationListParams = {}) {
    const { page = 1, size = 10, ...rest } = params;
    return httpJson<Paginated<CheckpointSignal>>(
      `/ui/checkpoint_signals${buildQuery({ page, size, ...rest })}`
    );
  },
  listAll(params: Omit<AssociationListParams, "page" | "size"> = {}) {
    return httpJson<CheckpointSignal[]>(
      `/ui/all_checkpoint_signals${buildQuery(params)}`
    );
  },
  create(payload: { checkpoint_id: string; signal_id: string }) {
    return httpJson<CheckpointSignal>("/ui/checkpoint_signals", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  },
  remove(id: string) {
    return httpJson<void>(`/ui/checkpoint_signals/${id}`, { method: "DELETE" });
  },
};
