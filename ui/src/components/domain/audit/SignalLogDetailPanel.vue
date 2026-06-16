<template>
  <div v-if="log" class="signal-log-detail-panel audit-console">
    <div
      class="audit-outcome-hero"
      :class="log.success === false ? 'audit-outcome-hero--fail' : 'audit-outcome-hero--ok'"
    >
      <StatusBadge :variant="statusVariant" :text="statusText" />
      <div class="audit-outcome-hero-body">
        <h4>{{ log.signal_name || log.signal_id || "Signal invocation" }}</h4>
        <p class="field-hint">{{ heroSubtitle }}</p>
      </div>
      <div class="audit-outcome-hero-metric">
        <span class="result-metric-label">Returned value</span>
        <span class="result-metric-value">{{ log.signal_value ?? "—" }}</span>
      </div>
    </div>

    <FormSection title="Invocation trace">
      <TraceTimeline :steps="traceSteps" />
    </FormSection>

    <FormSection title="Execution context">
      <dl class="detail-list">
        <div><dt>Applicant</dt><dd>{{ log.applicant_id || "—" }}</dd></div>
        <div><dt>Cost incurred</dt><dd>{{ formatCost(log.cost_incurred) }}</dd></div>
        <div><dt>Started</dt><dd>{{ formatTime(log.started_at) }}</dd></div>
        <div><dt>Completed</dt><dd>{{ formatTime(log.completed_at) }}</dd></div>
        <div v-if="log.decision_log_id"><dt>Decision log</dt><dd class="text-mono">{{ log.decision_log_id }}</dd></div>
      </dl>
    </FormSection>

    <FormSection v-if="log.param_values?.length" title="Parameters (redacted)">
      <dl class="detail-list">
        <div v-for="param in log.param_values" :key="param.param_name">
          <dt>{{ param.param_name }}</dt>
          <dd>{{ param.param_value ?? "—" }}</dd>
        </div>
      </dl>
    </FormSection>

    <FormSection title="Related resources">
      <div class="audit-related-links">
        <RouterLink
          v-if="log.signal_id"
          class="btn-secondary btn-sm"
          :to="signalLink"
        >
          Open signal
        </RouterLink>
        <RouterLink
          v-if="log.decision_log_id"
          class="btn-secondary btn-sm"
          :to="auditDecisionLink"
        >
          View parent decision
        </RouterLink>
        <RouterLink
          v-if="testLabLink"
          class="btn-primary btn-sm"
          :to="testLabLink"
        >
          Rerun in Test Lab
        </RouterLink>
      </div>
    </FormSection>

    <JsonInspector :data="log" summary="Raw signal log" />
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { RouterLink } from "vue-router";
import type { SignalLogSummary } from "@/api/types";
import { routeWithTenant } from "@/app/tenantNav";
import FormSection from "@/components/workbench/FormSection.vue";
import TraceTimeline, { type TraceStep } from "@/components/workbench/TraceTimeline.vue";
import StatusBadge from "@/components/workbench/StatusBadge.vue";
import JsonInspector from "@/components/workbench/JsonInspector.vue";

const props = defineProps<{
  log: SignalLogSummary | null;
}>();

const statusVariant = computed(() => (props.log?.success === false ? "inactive" : "current"));
const statusText = computed(() => (props.log?.success === false ? "Failed" : "OK"));

const heroSubtitle = computed(() => {
  if (!props.log) return "";
  if (props.log.success === false) {
    return "Signal execution failed during decision run — inspect trace and parameters below.";
  }
  return "Signal completed successfully for this invocation.";
});

const traceSteps = computed((): TraceStep[] => {
  const log = props.log;
  if (!log) return [];
  const steps: TraceStep[] = [];
  if (log.started_at) {
    steps.push({
      id: "started",
      label: "Invocation started",
      detail: formatTime(log.started_at),
      status: "neutral",
    });
  }
  steps.push({
    id: "evaluate",
    label: log.signal_name || "Signal evaluation",
    detail: log.success === false ? "Execution failed" : "Completed",
    value: log.signal_value,
    status: log.success === false ? "fail" : "ok",
  });
  if (log.completed_at) {
    steps.push({
      id: "completed",
      label: "Invocation completed",
      detail: formatTime(log.completed_at),
      status: log.success === false ? "fail" : "ok",
    });
  }
  return steps;
});

const signalLink = computed(() =>
  props.log?.signal_id
    ? routeWithTenant({ name: "signal-detail", params: { signalId: props.log.signal_id } })
    : routeWithTenant({ name: "signals" })
);

const auditDecisionLink = computed(() =>
  routeWithTenant({ name: "audit-decisions", query: { decision: props.log?.decision_log_id || "" } })
);

const testLabLink = computed(() => {
  if (!props.log) return null;
  const query: Record<string, string> = {};
  if (props.log.applicant_id) query.applicant = props.log.applicant_id;
  if (props.log.decision_log_id) query.from_decision = props.log.decision_log_id;
  if (!props.log.decision_log_id && !props.log.applicant_id) return null;
  return routeWithTenant({ name: "test-decisions", query });
});

function formatTime(value?: string) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

function formatCost(value?: number) {
  if (value == null) return "—";
  return value.toFixed(2);
}
</script>
