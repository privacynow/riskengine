<template>
  <div
    class="list-row entity-table-row list-row--workbench"
    :class="{ selected }"
  >
    <StatusBadge :variant="badgeVariant" :text="badgeText" />
    <button type="button" class="list-row-open" @click="$emit('open')">
      <span class="list-row-body">
        <span class="list-row-title">{{ promotion.resource_name }}</span>
        <span class="list-row-meta">{{ metaLine }}</span>
      </span>
      <span class="list-row-trailing">
        <span class="list-row-stats">
          <span class="list-row-time">{{ whenLabel }}</span>
        </span>
        <span class="list-row-action" aria-hidden="true">
          <Icon name="arrowRight" :size="14" />
        </span>
      </span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { PromotionAuditSummary } from "@/api/types";
import { formatDate, promotionActionBadgeVariant, promotionActionLabel } from "@/api/formatters";
import Icon from "@/components/primitives/Icon.vue";
import StatusBadge from "@/components/workbench/StatusBadge.vue";

const props = defineProps<{
  promotion: PromotionAuditSummary;
  selected?: boolean;
}>();

defineEmits<{
  open: [];
}>();

const badgeVariant = computed(() => promotionActionBadgeVariant(props.promotion.action));
const badgeText = computed(() => promotionActionLabel(props.promotion.action));
const metaLine = computed(() => {
  const parts = [
    props.promotion.resource_type === "signal" ? "Signal" : "Checkpoint",
    props.promotion.actor_id ? `Actor ${props.promotion.actor_id}` : null,
    props.promotion.promotion_reason,
  ].filter(Boolean);
  return parts.join(" · ");
});
const whenLabel = computed(() => formatDate(props.promotion.created_at));
</script>
