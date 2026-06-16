export type DslPreflightResult = {
  ok: boolean;
  errors: string[];
  warnings: string[];
};

export type DslPreflightOptions = {
  knownNames?: string[];
  bindingMode?: "strict" | "warn_unknown" | "syntax_only";
  expressionKind?: "checkpoint" | "signal_expression";
};
