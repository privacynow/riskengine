<template>
  <details class="json-inspector">
    <summary>{{ summary }}</summary>
    <pre>{{ formatted }}</pre>
  </details>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(
  defineProps<{
    data: unknown;
    summary?: string;
  }>(),
  { summary: "Raw JSON" }
);

const formatted = computed(() => {
  try {
    return JSON.stringify(props.data, null, 2);
  } catch {
    return String(props.data);
  }
});
</script>
