<template>
  <div
    v-if="selectable"
    class="list-row entity-table-row list-row--workbench"
    :class="{ selected }"
  >
    <StatusBadge :variant="statusVariant" :text="statusText" />
    <button type="button" class="list-row-open" @click="$emit('open')">
      <span class="list-row-body">
        <span class="list-row-title">{{ signalName }}</span>
        <span class="list-row-meta">{{ metaLine }}</span>
      </span>
      <span class="list-row-trailing">
        <span class="list-row-stats">
          <span v-if="costLabel" class="list-row-cost">{{ costLabel }}</span>
          <span class="list-row-time">{{ whenLabel }}</span>
        </span>
        <span class="list-row-action" aria-hidden="true">
          <Icon name="arrowRight" :size="14" />
        </span>
      </span>
    </button>
  </div>
  <RouterLink
    v-else
    :to="to!"
    class="list-row"
    :class="{ selected: selected ? 'selected' : undefined, 'entity-table-row': selected !== undefined }"
  >
    <StatusBadge :variant="statusVariant" :text="statusText" />
    <div class="list-row-body">
      <span class="list-row-title">{{ signalName }}</span>
      <span class="list-row-meta">{{ metaLine }}</span>
    </div>
    <div class="list-row-trailing">
      <div class="list-row-stats">
        <span v-if="costLabel" class="list-row-cost">{{ costLabel }}</span>
        <span class="list-row-time">{{ whenLabel }}</span>
      </div>
      <span class="list-row-action" aria-hidden="true">
        <Icon name="arrowRight" :size="14" />
      </span>
    </div>
  </RouterLink>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, type RouteLocationRaw } from "vue-router";
import type { SignalLogSummary } from "@/api/types";
import { formatDate } from "@/api/formatters";
import Icon from "@/components/primitives/Icon.vue";
import StatusBadge from "@/components/workbench/StatusBadge.vue";

const props = defineProps<{
  log: SignalLogSummary;
  to?: RouteLocationRaw;
  selected?: boolean;
}>();

defineEmits<{
  open: [];
}>();

const selectable = computed(() => !props.to);

const statusVariant = computed(() => (props.log.success === false ? "inactive" : "current"));
const statusText = computed(() => (props.log.success === false ? "Failed" : "OK"));
const signalName = computed(() => props.log.signal_name || "Unknown signal");
const metaLine = computed(() => {
  const parts = [
    props.log.applicant_id ? `Applicant ${props.log.applicant_id}` : null,
    props.log.signal_value != null && props.log.signal_value !== ""
      ? `Value ${props.log.signal_value}`
      : null,
  ].filter(Boolean);
  return parts.length ? parts.join(" · ") : "No applicant or value recorded";
});
const costLabel = computed(() => {
  const cost = props.log.cost_incurred;
  if (cost == null || cost <= 0) return "";
  return `Cost ${cost.toFixed(2)}`;
});
const whenLabel = computed(() => formatDate(props.log.started_at || props.log.created_at));
</script>
