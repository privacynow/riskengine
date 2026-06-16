import { httpJson } from "@/api/httpClient";

export type DslPreflightResult = {
  ok: boolean;
  errors: string[];
  warnings: string[];
};

export const dslApi = {
  preflight(dslExpression: string, signalNames: string[] = []) {
    return httpJson<DslPreflightResult>("/ui/dsl_preflight", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        dsl_expression: dslExpression,
        signal_names: signalNames,
      }),
    });
  },
};
