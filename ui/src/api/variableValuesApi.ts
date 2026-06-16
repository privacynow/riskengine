import { httpJson } from "@/api/httpClient";
import type { AdminMutationResponse, VariableValue } from "@/api/types";

export const variableValuesApi = {
  upsert(payload: { signal_id: string; name: string; value?: string }) {
    return httpJson<AdminMutationResponse>("/ui/variable_values", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  },
  get(id: string) {
    return httpJson<VariableValue>(`/ui/variable_values/${id}`);
  },
  update(id: string, payload: { signal_id: string; name: string; value?: string }) {
    return httpJson<VariableValue>(`/ui/variable_values/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  },
  remove(id: string) {
    return httpJson<AdminMutationResponse>(`/ui/variable_values/${id}`, {
      method: "DELETE",
    });
  },
};
