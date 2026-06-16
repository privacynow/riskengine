<template>
  <ul class="trace-timeline">
    <li
      v-for="step in steps"
      :key="step.id"
      class="trace-step"
      :class="stepClass(step)"
    >
      <strong>{{ step.label }}</strong>
      <span v-if="step.detail" class="text-muted"> — {{ step.detail }}</span>
      <div v-if="step.value !== undefined" class="field-hint">{{ formatValue(step.value) }}</div>
    </li>
  </ul>
</template>

<script setup lang="ts">
export type TraceStep = {
  id: string;
  label: string;
  detail?: string;
  value?: unknown;
  status?: "ok" | "fail" | "neutral";
};

defineProps<{
  steps: TraceStep[];
}>();

function stepClass(step: TraceStep) {
  if (step.status === "ok") return "trace-step--ok";
  if (step.status === "fail") return "trace-step--fail";
  return "";
}

function formatValue(value: unknown) {
  if (typeof value === "object") {
    try {
      return JSON.stringify(value);
    } catch {
      return String(value);
    }
  }
  return String(value);
}
</script>
