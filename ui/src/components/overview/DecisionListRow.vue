<template>
  <div
    v-if="selectable"
    class="list-row entity-table-row list-row--workbench"
    :class="{ selected }"
  >
    <StatusBadge :variant="outcomeVariant" :text="outcomeLabel" />
    <button type="button" class="list-row-open" @click="$emit('open')">
      <span class="list-row-body">
        <span class="list-row-title">{{ flowName }}</span>
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
    <StatusBadge :variant="outcomeVariant" :text="outcomeLabel" />
    <div class="list-row-body">
      <span class="list-row-title">{{ flowName }}</span>
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
import type { DecisionSummary } from "@/api/types";
import { decisionOutcomeVariant, formatDate } from "@/api/formatters";
import Icon from "@/components/primitives/Icon.vue";
import StatusBadge from "@/components/workbench/StatusBadge.vue";

const props = defineProps<{
  decision: DecisionSummary;
  to?: RouteLocationRaw;
  selected?: boolean;
}>();

defineEmits<{
  open: [];
}>();

const selectable = computed(() => !props.to);

const outcomeLabel = computed(() => props.decision.final_decision_value || "—");
const outcomeVariant = computed(() => decisionOutcomeVariant(props.decision.final_decision_value));
const flowName = computed(() => props.decision.checkpoint_name || "Unknown checkpoint");
const metaLine = computed(() => {
  const parts = [
    props.decision.applicant_id ? `Applicant ${props.decision.applicant_id}` : null,
    props.decision.correlation_id ? `Corr ${props.decision.correlation_id}` : null,
  ].filter(Boolean);
  return parts.length ? parts.join(" · ") : "No applicant or correlation";
});
const costLabel = computed(() => {
  const cost = props.decision.cost_incurred;
  if (cost == null || cost <= 0) return "";
  return `Cost ${cost.toFixed(2)}`;
});
const whenLabel = computed(() =>
  formatDate(props.decision.decision_timestamp || props.decision.created_at)
);
</script>
