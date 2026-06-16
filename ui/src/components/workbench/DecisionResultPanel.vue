<template>
  <div v-if="result" class="decision-result">
    <div v-if="error" class="inline-error" role="alert">{{ error }}</div>
    <template v-else>
      <div class="result-summary">
        <div class="result-metric">
          <div class="result-metric-label">Decision</div>
          <div class="result-metric-value">{{ finalValue }}</div>
        </div>
        <div class="result-metric">
          <div class="result-metric-label">Cost</div>
          <div class="result-metric-value">{{ cost }}</div>
        </div>
        <div v-if="decisionId" class="result-metric">
          <div class="result-metric-label">Decision ID</div>
          <div class="result-metric-value text-mono">{{ decisionId }}</div>
        </div>
      </div>

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
import FormSection from "@/components/workbench/FormSection.vue";
import TraceTimeline, { type TraceStep } from "@/components/workbench/TraceTimeline.vue";
import JsonInspector from "@/components/workbench/JsonInspector.vue";

const props = defineProps<{
  result: DecisionTestResponse | Record<string, unknown> | null;
}>();

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
