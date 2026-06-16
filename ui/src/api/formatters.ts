export function isEndpointSignalType(type: string): boolean {
  return type === "internal_endpoint" || type === "external_endpoint";
}

export function signalTypeBadge(type: string): string {
  if (isEndpointSignalType(type)) return "endpoint";
  if (type === "function") return "function";
  if (type === "variable") return "variable";
  return "inactive";
}

export function signalTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    internal_endpoint: "Internal endpoint",
    external_endpoint: "External endpoint",
    function: "Function",
    variable: "Variable",
    expression: "Expression",
  };
  return labels[type] || type || "Unknown";
}

export function formatDate(value: string | undefined | null): string {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return String(value);
  }
}

export function decisionOutcomeVariant(value?: string): string {
  const normalized = (value || "").trim().toLowerCase();
  if (!normalized) return "outcome-neutral";
  if (["approve", "approved", "pass", "accept", "yes", "true"].some((k) => normalized.includes(k))) {
    return "outcome-positive";
  }
  if (["deny", "denied", "reject", "rejected", "fail", "failed", "no", "false"].some((k) => normalized.includes(k))) {
    return "outcome-negative";
  }
  return "outcome-neutral";
}

export function formatJson(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

export function isCurrentVersion(
  row: { is_current_version?: boolean } | null | undefined
): boolean {
  return !!row?.is_current_version;
}

/** Checkpoint max_cost cap label — undefined means no cap configured. */
export function formatCheckpointCostCap(maxCost?: number): string {
  if (maxCost == null) return "No cap";
  return `Cap ${maxCost.toFixed(2)}`;
}

/** Per-invocation signal cost label. */
export function formatSignalRuntimeCost(cost?: number): string {
  if (cost == null || cost <= 0) return "No runtime cost";
  return `Cost ${cost.toFixed(2)}`;
}

export function formatEvalTimeout(seconds?: number): string {
  if (seconds == null) return "";
  return `${seconds}s eval limit`;
}

export function promotionActionLabel(action?: string): string {
  const labels: Record<string, string> = {
    promote: "Promote",
    deactivate: "Deactivate",
    reactivate: "Reactivate",
  };
  if (!action) return "Promote";
  return labels[action] || action;
}

export function promotionActionBadgeVariant(action?: string): string {
  if (action === "deactivate") return "inactive";
  return "current";
}

export function canPromoteVersion(item: {
  is_current_version?: boolean;
  name_has_current_version?: boolean;
}): boolean {
  return !item.is_current_version && !!item.name_has_current_version;
}

export function canReactivateVersion(item: {
  is_current_version?: boolean;
  name_has_current_version?: boolean;
}): boolean {
  return !item.is_current_version && item.name_has_current_version === false;
}
