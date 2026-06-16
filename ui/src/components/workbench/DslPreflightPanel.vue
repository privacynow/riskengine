<template>
  <div class="dsl-preflight-panel" :class="panelClass">
    <div class="dsl-preflight-header">
      <Icon :name="statusIcon" :size="16" />
      <span class="dsl-preflight-title">{{ statusTitle }}</span>
      <span v-if="loading" class="text-muted">Checking…</span>
    </div>
    <p v-if="statusHint" class="field-hint">{{ statusHint }}</p>
    <ul v-if="errors.length" class="dsl-preflight-list dsl-preflight-list--error">
      <li v-for="(item, index) in errors" :key="'err-' + index">{{ item }}</li>
    </ul>
    <ul v-if="warnings.length" class="dsl-preflight-list dsl-preflight-list--warn">
      <li v-for="(item, index) in warnings" :key="'warn-' + index">{{ item }}</li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { dslApi } from "@/api/dslApi";
import Icon from "@/components/primitives/Icon.vue";
import type { IconName } from "@/icons";

const props = withDefaults(
  defineProps<{
    expression: string;
    signalNames?: string[];
    autoCheck?: boolean;
  }>(),
  {
    signalNames: () => [],
    autoCheck: true,
  }
);

const loading = ref(false);
const ok = ref<boolean | null>(null);
const errors = ref<string[]>([]);
const warnings = ref<string[]>([]);

let debounceTimer: number | null = null;

const panelClass = computed(() => {
  if (loading.value) return "dsl-preflight-panel--pending";
  if (ok.value === true) return "dsl-preflight-panel--ok";
  if (ok.value === false) return "dsl-preflight-panel--fail";
  return "dsl-preflight-panel--idle";
});

const statusIcon = computed((): IconName => {
  if (loading.value) return "refresh";
  if (ok.value === true) return "zap";
  if (ok.value === false) return "alert";
  return "layers";
});

const statusTitle = computed(() => {
  if (loading.value) return "DSL preflight";
  if (ok.value === true) return "DSL preflight passed";
  if (ok.value === false) return "DSL preflight failed";
  return "DSL preflight";
});

const statusHint = computed(() => {
  if (!props.expression.trim()) return "Enter a DSL expression to validate syntax before save or promotion.";
  if (ok.value === true && !warnings.value.length) {
    return "Expression syntax is valid and all identifiers match associated signals.";
  }
  return "";
});

async function runPreflight() {
  const expr = props.expression.trim();
  if (!expr) {
    ok.value = null;
    errors.value = [];
    warnings.value = [];
    return;
  }
  loading.value = true;
  try {
    const result = await dslApi.preflight(expr, props.signalNames);
    ok.value = result.ok;
    errors.value = result.errors ?? [];
    warnings.value = result.warnings ?? [];
  } catch {
    ok.value = false;
    errors.value = ["Preflight request failed. Check connectivity and try again."];
    warnings.value = [];
  } finally {
    loading.value = false;
  }
}

function schedulePreflight() {
  if (!props.autoCheck) return;
  if (debounceTimer) window.clearTimeout(debounceTimer);
  debounceTimer = window.setTimeout(() => {
    void runPreflight();
  }, 350);
}

watch(
  () => [props.expression, props.signalNames.join("|")] as const,
  () => schedulePreflight(),
  { immediate: true }
);

defineExpose({ runPreflight, ok, errors, warnings, loading });
</script>
