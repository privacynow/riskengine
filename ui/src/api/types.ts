export type SignalType =
  | "variable"
  | "function"
  | "internal_endpoint"
  | "external_endpoint"
  | "expression";

export type Paginated<T> = {
  items: T[];
  total: number;
  page: number;
  size: number;
  total_pages?: number;
};

export type Tenant = {
  id: string;
  name: string;
  active?: boolean;
};

export type Checkpoint = {
  id: string;
  tenant_id: string;
  name: string;
  description?: string;
  type?: string;
  dsl_expression?: string;
  method_of_call?: string;
  max_cost?: number;
  override_cost_flag?: boolean;
  timeout_seconds?: number;
  is_current_version?: boolean;
  name_has_current_version?: boolean;
  updated_at?: string;
};

export type Signal = {
  id: string;
  tenant_id: string;
  name: string;
  description?: string;
  type: SignalType | string;
  method_of_call?: string;
  expression_body?: string;
  cost?: number;
  cache_expiration_seconds?: number;
  timeout_seconds?: number;
  can_run_in_parallel?: boolean;
  order_of_evaluation?: number;
  http_method?: string;
  has_bearer_token?: boolean;
  request_url_params_template?: string;
  request_body_template?: string;
  request_headers_template?: string;
  allow_caching?: boolean;
  global_reuse?: boolean;
  function_params_template?: string;
  is_current_version?: boolean;
  name_has_current_version?: boolean;
  param_placeholders?: string[];
  updated_at?: string;
};

export type CheckpointSignal = {
  id: string;
  checkpoint_id: string;
  signal_id: string;
  checkpoint_name?: string;
  signal_name?: string;
  priority_override?: number | null;
  criticality?: string;
  execution_role?: string;
  stage_override?: number | null;
  vendor_audit_after_decline?: boolean;
};

export type DecisionSummary = {
  id: string;
  tenant_id?: string;
  checkpoint_id?: string;
  checkpoint_name?: string;
  applicant_id?: string;
  correlation_id?: string;
  final_decision_value?: string;
  decision_outcome?: string;
  decision_reason?: string;
  degraded?: boolean;
  cost_incurred?: number;
  decision_timestamp?: string;
  /** @deprecated use decision_timestamp */
  created_at?: string;
};

export type SignalLogParam = {
  param_name: string;
  param_value?: string;
};

export type SignalLogSummary = {
  id: string;
  decision_log_id?: string;
  signal_id?: string;
  signal_name?: string;
  signal_value?: string;
  success?: boolean;
  cost_incurred?: number;
  started_at?: string;
  completed_at?: string;
  applicant_id?: string;
  param_values?: SignalLogParam[];
  /** @deprecated use started_at */
  created_at?: string;
};

export type DecisionSignalTrace = {
  signal_log_id?: string;
  signal_id?: string;
  signal_name?: string;
  signal_type?: string;
  signal_value?: unknown;
  success?: boolean;
  cost_incurred?: number;
  started_at?: string;
  completed_at?: string;
  param_values?: Record<string, string>;
};

export type DecisionDetail = {
  id: string;
  checkpoint_id?: string;
  checkpoint_name?: string;
  checkpoint_dsl_expression?: string;
  decorated_dsl_expression?: string;
  tenant_id?: string;
  applicant_id?: string;
  correlation_id?: string;
  final_decision_value?: string;
  decision_outcome?: string;
  decision_reason?: string;
  degraded?: boolean;
  cost_incurred?: number;
  decision_timestamp?: string;
  signals?: DecisionSignalTrace[];
};

export type DecisionTestPayload = {
  tenant_id: string;
  checkpoint_name: string;
  checkpoint_id?: string;
  applicant_id?: string;
  correlation_id?: string;
  parameters?: Record<string, string>;
};

export type DecisionCostSummary = {
  estimated_units: number;
  reserved_units: number;
  actual_units: number;
  budget_units?: number | null;
  tenant_budget_remaining_units?: number | null;
};

export type SignalExecutionSummary = {
  name: string;
  status: string;
  criticality: string;
  estimated_cost_units: number;
  reserved_cost_units: number;
  actual_cost_units: number;
  cache_hit: boolean;
  skip_reason?: string | null;
  value?: unknown;
};

export type DecisionTestResponse = {
  decision_id: string;
  decision_outcome: string;
  decision_reason: string;
  degraded: boolean;
  cost: DecisionCostSummary;
  signals: SignalExecutionSummary[];
  signal_results: Record<string, unknown>;
};

export type AdminMutationResponse = {
  ok: true;
  action: string;
  id: string;
  [key: string]: unknown;
};

export type VariableValue = {
  id: string;
  signal_id: string;
  name: string;
  value?: string;
};

export type SignalDraft = {
  id?: string;
  name: string;
  description: string;
  type: SignalType | string;
  method_of_call: string;
  expression_body: string;
  cost: number;
  cache_expiration_seconds: number;
  timeout_seconds: number;
  can_run_in_parallel: boolean;
  order_of_evaluation: number;
  http_method: string;
  bearer_token: string;
  request_url_params_template: string;
  request_body_template: string;
  request_headers_template: string;
  allow_caching: boolean;
  global_reuse: boolean;
  function_params_template: string;
};

export type PromotionAuditSummary = {
  id: string;
  tenant_id: string;
  resource_type: "checkpoint" | "signal" | string;
  resource_id: string;
  resource_name: string;
  actor_id: string;
  promotion_reason: string;
  action?: "promote" | "deactivate" | "reactivate" | string;
  source?: string;
  created_at?: string;
};

export type CheckpointDraft = {
  id?: string;
  name: string;
  description: string;
  type: string;
  dsl_expression: string;
  method_of_call: string;
  max_cost: number;
  override_cost_flag: boolean;
  timeout_seconds: number;
  signalSearch: string;
  signalSearchResults: Signal[];
  associatedSignals: Signal[];
  signalPage: number;
  signalTotalPages: number;
  signalSize: number;
};

export function emptySignalDraft(): SignalDraft {
  return {
    name: "",
    description: "",
    type: "variable",
    method_of_call: "",
    expression_body: "",
    cost: 0,
    cache_expiration_seconds: 0,
    timeout_seconds: 30,
    can_run_in_parallel: false,
    order_of_evaluation: 1,
    http_method: "GET",
    bearer_token: "",
    request_url_params_template: "",
    request_body_template: "",
    request_headers_template: "",
    allow_caching: false,
    global_reuse: false,
    function_params_template: "",
  };
}

export function emptyCheckpointDraft(): CheckpointDraft {
  return {
    name: "",
    description: "",
    type: "",
    dsl_expression: "",
    method_of_call: "",
    max_cost: 0,
    override_cost_flag: false,
    timeout_seconds: 30,
    signalSearch: "",
    signalSearchResults: [],
    associatedSignals: [],
    signalPage: 1,
    signalTotalPages: 1,
    signalSize: 5,
  };
}

export function signalToDraft(signal: Signal): SignalDraft {
  return {
    id: signal.id,
    name: signal.name,
    description: signal.description || "",
    type: signal.type,
    method_of_call: signal.method_of_call || "",
    expression_body: signal.expression_body || "",
    cost: signal.cost ?? 0,
    cache_expiration_seconds: signal.cache_expiration_seconds ?? 0,
    timeout_seconds: signal.timeout_seconds ?? 30,
    can_run_in_parallel: signal.can_run_in_parallel ?? false,
    order_of_evaluation: signal.order_of_evaluation ?? 1,
    http_method: signal.http_method || "GET",
    bearer_token: "",
    request_url_params_template: signal.request_url_params_template || "",
    request_body_template: signal.request_body_template || "",
    request_headers_template: signal.request_headers_template || "",
    allow_caching: signal.allow_caching ?? false,
    global_reuse: signal.global_reuse ?? false,
    function_params_template: signal.function_params_template || "",
  };
}

export function checkpointToDraft(checkpoint: Checkpoint): CheckpointDraft {
  return {
    ...emptyCheckpointDraft(),
    id: checkpoint.id,
    name: checkpoint.name,
    description: checkpoint.description || "",
    type: checkpoint.type || "",
    dsl_expression: checkpoint.dsl_expression || "",
    method_of_call: checkpoint.method_of_call || "",
    max_cost: checkpoint.max_cost ?? 0,
    override_cost_flag: checkpoint.override_cost_flag ?? false,
    timeout_seconds: checkpoint.timeout_seconds ?? 30,
  };
}

export function totalPages(total: number, size: number): number {
  return Math.max(1, Math.ceil(total / size));
}
