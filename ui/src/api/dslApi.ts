import type { DslPreflightOptions, DslPreflightResult } from "@/api/dslTypes";
import { httpJson } from "@/api/httpClient";

export type { DslPreflightOptions, DslPreflightResult };

export const dslApi = {
  preflight(
    dslExpression: string,
    signalNames: string[] = [],
    options: DslPreflightOptions = {}
  ) {
    return httpJson<DslPreflightResult>("/ui/dsl_preflight", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        dsl_expression: dslExpression,
        checkpoint_id: options.checkpointId,
        signal_names: signalNames,
        known_names: options.knownNames ?? [],
        binding_mode: options.bindingMode,
        expression_kind: options.expressionKind ?? "checkpoint",
      }),
    });
  },
};
