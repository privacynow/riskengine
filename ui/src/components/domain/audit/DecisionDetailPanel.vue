<template>
  <div v-if="detail" class="decision-detail-panel">
    <div class="result-summary">
      <div class="result-metric">
        <div class="result-metric-label">Result</div>
        <div class="result-metric-value">{{ detail.final_decision_value || "—" }}</div>
      </div>
      <div class="result-metric">
        <div class="result-metric-label">Cost</div>
        <div class="result-metric-value">{{ detail.cost_incurred ?? "—" }}</div>
      </div>
      <div class="result-metric">
        <div class="result-metric-label">Checkpoint</div>
        <div class="result-metric-value">{{ detail.checkpoint_name || "—" }}</div>
      </div>
    </div>

    <dl class="detail-list">
      <div><dt>Applicant</dt><dd>{{ detail.applicant_id || "—" }}</dd></div>
      <div><dt>Correlation</dt><dd>{{ detail.correlation_id || "—" }}</dd></div>
      <div><dt>Timestamp</dt><dd>{{ formatTime(detail.decision_timestamp) }}</dd></div>
    </dl>

    <FormSection v-if="detail.decorated_dsl_expression || detail.checkpoint_dsl_expression" title="DSL evaluation">
      <pre class="code-block">{{ detail.decorated_dsl_expression || detail.checkpoint_dsl_expression }}</pre>
    </FormSection>

    <FormSection v-if="traceSteps.length" title="Signal execution">
      <TraceTimeline :steps="traceSteps" />
    </FormSection>

    <div class="form-actions">
      <RouterLink
        v-if="detail.checkpoint_id"
        class="btn-secondary btn-sm"
        :to="checkpointLink"
      >
        Open checkpoint
      </RouterLink>
      <RouterLink class="btn-primary btn-sm" :to="testLink">Run similar test</RouterLink>
    </div>

    <JsonInspector :data="detail" summary="Raw decision record" />
  </div>
  <LoadingSkeleton v-else-if="loading" block />
</template>

<script setup lang="ts">
import { computed } from "vue";
import { RouterLink } from "vue-router";
import type { DecisionDetail } from "@/api/types";
import { routeWithTenant } from "@/app/tenantNav";
import FormSection from "@/components/workbench/FormSection.vue";
import TraceTimeline, { type TraceStep } from "@/components/workbench/TraceTimeline.vue";
import JsonInspector from "@/components/workbench/JsonInspector.vue";
import LoadingSkeleton from "@/components/workbench/LoadingSkeleton.vue";

const props = defineProps<{
  detail: DecisionDetail | null;
  loading?: boolean;
}>();

const traceSteps = computed((): TraceStep[] => {
  const signals = props.detail?.signals ?? [];
  return signals.map((sig) => ({
    id: sig.signal_log_id || sig.signal_name || String(sig.signal_id),
    label: sig.signal_name || "signal",
    detail: sig.success === false ? "failed" : "ok",
    value: sig.signal_value,
    status: sig.success === false ? "fail" : "ok",
  }));
});

const checkpointLink = computed(() =>
  props.detail?.checkpoint_id
    ? routeWithTenant({
        name: "checkpoint-detail",
        params: { checkpointId: props.detail.checkpoint_id },
      })
    : routeWithTenant({ name: "checkpoints" })
);

const testLink = computed(() => {
  const query: Record<string, string> = {};
  if (props.detail?.checkpoint_id) query.checkpoint = props.detail.checkpoint_id;
  if (props.detail?.applicant_id) query.applicant = props.detail.applicant_id;
  if (props.detail?.correlation_id) query.correlation = props.detail.correlation_id;
  if (props.detail?.id) query.from_decision = props.detail.id;
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
</script>
