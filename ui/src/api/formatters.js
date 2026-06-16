export function isEndpointSignalType(type) {
  return type === "internal_endpoint" || type === "external_endpoint";
}

export function signalTypeBadge(type) {
  if (type === "internal_endpoint" || type === "external_endpoint") return "endpoint";
  if (type === "function") return "function";
  if (type === "variable") return "variable";
  return "inactive";
}

export function signalTypeLabel(type) {
  const labels = {
    internal_endpoint: "Internal endpoint",
    external_endpoint: "External endpoint",
    function: "Function",
    variable: "Variable",
  };
  return labels[type] || type || "Unknown";
}

export function formatDate(value) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return String(value);
  }
}

export function formatJson(value) {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}
