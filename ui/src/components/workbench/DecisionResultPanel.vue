<template>
  <div v-if="result" class="decision-result" :class="{ 'decision-result--harness': variant === 'harness' }">
    <div v-if="error" class="inline-error" role="alert">{{ error }}</div>
    <template v-else>
      <div
        class="audit-outcome-hero test-result-hero"
        :class="outcomeHeroClass"
      >
        <StatusBadge :variant="outcomeVariant" :text="finalValue" />
        <div class="audit-outcome-hero-body">
          <h4>{{ variant === 'harness' ? 'Test run result' : 'Decision outcome' }}</h4>
          <p class="field-hint">{{ outcomeHint }}</p>
        </div>
        <div class="audit-outcome-hero-metric">
          <span class="result-metric-label">Cost</span>
          <span class="result-metric-value">{{ cost }}</span>
        </div>
      </div>

      <dl v-if="decisionId" class="detail-list detail-list--compact">
        <div><dt>Decision ID</dt><dd class="text-mono">{{ decisionId }}</dd></div>
      </dl>

      <FormSection v-if="traceSteps.length" title="Signal trace">
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
  if ("final_decision_value" in r && "signal_results" in r) {
    return r as DecisionTestResponse;
  }
  return null;
});

const finalValue = computed(() => normalized.value?.final_decision_value ?? "—");
const cost = computed(() => normalized.value?.cost_incurred ?? "—");
const decisionId = computed(() => normalized.value?.decision_id ?? "");
const outcomeVariant = computed(() => decisionOutcomeVariant(normalized.value?.final_decision_value));

const outcomeHeroClass = computed(() => {
  const value = String(finalValue.value).toLowerCase();
  if (value === "false" || value === "fail" || value === "failed") {
    return "audit-outcome-hero--fail";
  }
  if (value === "true" || value === "pass" || value === "approved") {
    return "audit-outcome-hero--ok";
  }
  return "audit-outcome-hero--neutral";
});

const outcomeHint = computed(() => {
  if (props.variant === "harness") {
    return "Server-side test execution — not promoted to production traffic.";
  }
  return "Final evaluated decision value for this run.";
});

const traceSteps = computed((): TraceStep[] => {
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
