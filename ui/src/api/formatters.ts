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
