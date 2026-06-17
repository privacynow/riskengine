<template>
  <div v-if="result" class="decision-result" :class="{ 'decision-result--harness': variant === 'harness' }">
    <div v-if="error" class="inline-error" role="alert">{{ error }}</div>
    <template v-else>
      <div
        class="audit-outcome-hero test-result-hero"
        :class="outcomeHeroClass"
      >
        <StatusBadge :variant="outcomeVariant" :text="outcomeLabel" />
        <div class="audit-outcome-hero-body">
          <h4>{{ variant === 'harness' ? 'Test run result' : 'Decision outcome' }}</h4>
          <p class="field-hint">{{ outcomeHint }}</p>
        </div>
        <div class="audit-outcome-hero-metric">
          <span class="result-metric-label">Actual cost</span>
          <span class="result-metric-value">{{ cost }}</span>
        </div>
      </div>

      <dl v-if="decisionId" class="detail-list detail-list--compact">
        <div><dt>Decision ID</dt><dd class="text-mono">{{ decisionId }}</dd></div>
        <div v-if="decisionReason"><dt>Reason</dt><dd>{{ decisionReason }}</dd></div>
        <div v-if="degraded"><dt>Degraded</dt><dd>Non-required signals missing or failed</dd></div>
      </dl>

      <FormSection v-if="traceSteps.length" title="Execution plan">
        <TraceTimeline :steps="traceSteps" />
      </FormSection>

      <JsonInspector :data="result" />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { DecisionTestResponse } from "@/api/types";
import { decisionOutcomeVariant } from "@/api/formatters";
import FormSection from "@/components/workbench/FormSection.vue";
import TraceTimeline, { type TraceStep } from "@/components/workbench/TraceTimeline.vue";
import StatusBadge from "@/components/workbench/StatusBadge.vue";
import JsonInspector from "@/components/workbench/JsonInspector.vue";

const props = withDefaults(
  defineProps<{
    result: DecisionTestResponse | Record<string, unknown> | null;
    variant?: "default" | "harness";
  }>(),
  { variant: "default" }
);

const error = computed(() => {
  const r = props.result;
  if (!r || !("error" in r)) return "";
  return String((r as { error: unknown }).error);
});

const normalized = computed((): DecisionTestResponse | null => {
  const r = props.result;
  if (!r || error.value) return null;
  if ("decision_outcome" in r && "signal_results" in r) {
    return r as DecisionTestResponse;
  }
  return null;
});

const outcomeLabel = computed(() => {
  const outcome = normalized.value?.decision_outcome ?? "—";
  if (normalized.value?.degraded && outcome === "APPROVE") {
    return "APPROVE (degraded)";
  }
  return outcome;
});
const cost = computed(() => normalized.value?.cost?.actual_units ?? "—");
const decisionId = computed(() => normalized.value?.decision_id ?? "");
const decisionReason = computed(() => normalized.value?.decision_reason ?? "");
const degraded = computed(() => normalized.value?.degraded ?? false);
const outcomeVariant = computed(() => decisionOutcomeVariant(normalized.value?.decision_outcome));

const outcomeHeroClass = computed(() => {
  const value = String(normalized.value?.decision_outcome ?? "").toUpperCase();
  if (value === "DECLINE" || value === "ERROR") return "audit-outcome-hero--fail";
  if (value === "APPROVE") return "audit-outcome-hero--ok";
  if (value === "REFER" || value === "INCOMPLETE") return "audit-outcome-hero--neutral";
  return "audit-outcome-hero--neutral";
});

const outcomeHint = computed(() => {
  if (props.variant === "harness") {
    return "Server-side test execution — not promoted to production traffic.";
  }
  return normalized.value?.decision_reason || "Structured decision outcome for this run.";
});

const traceSteps = computed((): TraceStep[] => {
  const signals = normalized.value?.signals;
  if (signals?.length) {
    return signals.map((sig) => ({
      id: sig.name,
      label: sig.name,
      detail: sig.skip_reason || sig.status,
      value: sig.value,
      status:
        sig.status === "ran"
          ? "ok"
          : sig.status.startsWith("skipped") || sig.status === "not_applicable"
            ? "neutral"
            : "fail",
    }));
  }
  const results = normalized.value?.signal_results;
  if (!results) return [];
  return Object.entries(results).map(([name, value]) => ({
    id: name,
    label: name,
    value,
    status: value === false || value === null ? "fail" : "ok",
  }));
});
</script>
