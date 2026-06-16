import { buildQuery, httpJson } from "@/api/httpClient";
import type { AdminMutationResponse, Checkpoint, Paginated } from "@/api/types";

export type CheckpointListParams = {
  page: number;
  size: number;
  tenant_id?: string;
  active_only?: boolean;
  checkpoint_id?: string;
};

export const checkpointsApi = {
  list(params: CheckpointListParams) {
    return httpJson<Paginated<Checkpoint>>(`/ui/checkpoints${buildQuery(params)}`);
  },
  search(params: CheckpointListParams & { q: string }) {
    return httpJson<Paginated<Checkpoint>>(
      `/ui/search_checkpoints${buildQuery(params)}`
    );
  },
  get(id: string) {
    return httpJson<Checkpoint>(`/ui/checkpoints/${id}`);
  },
  create(payload: Record<string, unknown>) {
    return httpJson<AdminMutationResponse>("/ui/checkpoints", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  },
  update(id: string, payload: Record<string, unknown>) {
    return httpJson<Checkpoint>(`/ui/checkpoints/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  },
  makeCurrent(id: string, payload: Record<string, unknown>) {
    return httpJson<unknown>(`/ui/checkpoints/${id}/make_current`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  },
};
