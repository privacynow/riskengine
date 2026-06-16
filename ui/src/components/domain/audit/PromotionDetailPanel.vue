<template>
  <div v-if="promotion" class="promotion-detail-panel audit-console">
    <div class="audit-outcome-hero audit-outcome-hero--neutral">
      <StatusBadge :variant="badgeVariant" :text="badgeText" />
      <div class="audit-outcome-hero-body">
        <h4>{{ promotion.resource_name }}</h4>
        <p class="field-hint">{{ heroHint }}</p>
      </div>
      <div class="audit-outcome-hero-metric">
        <span class="result-metric-label">Actor</span>
        <span class="result-metric-value">{{ promotion.actor_id }}</span>
      </div>
    </div>

    <FormSection title="Governance reason">
      <p class="promotion-reason-copy">{{ promotion.promotion_reason }}</p>
    </FormSection>

    <FormSection title="Resource context">
      <dl class="detail-list">
        <div><dt>Action</dt><dd>{{ actionLabel }}</dd></div>
        <div><dt>Resource type</dt><dd>{{ resourceTypeLabel }}</dd></div>
        <div><dt>Resource ID</dt><dd class="text-mono">{{ promotion.resource_id }}</dd></div>
        <div><dt>Source</dt><dd>{{ promotion.source || "make_current" }}</dd></div>
        <div><dt>Recorded</dt><dd>{{ formatTime(promotion.created_at) }}</dd></div>
      </dl>
    </FormSection>

    <div class="audit-related-links">
      <RouterLink
        v-if="promotion.resource_type === 'checkpoint'"
        class="btn-secondary btn-sm"
        :to="flowLink"
      >
        Open checkpoint
      </RouterLink>
      <RouterLink
        v-else-if="promotion.resource_type === 'signal'"
        class="btn-secondary btn-sm"
        :to="signalLink"
      >
        Open signal
      </RouterLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { RouterLink } from "vue-router";
import type { PromotionAuditSummary } from "@/api/types";
import { promotionActionBadgeVariant, promotionActionLabel } from "@/api/formatters";
import { routeWithTenant } from "@/app/tenantNav";
import FormSection from "@/components/workbench/FormSection.vue";
import StatusBadge from "@/components/workbench/StatusBadge.vue";

const props = defineProps<{
  promotion: PromotionAuditSummary | null;
}>();

const actionLabel = computed(() => promotionActionLabel(props.promotion?.action));
const resourceTypeLabel = computed(() =>
  props.promotion?.resource_type === "signal" ? "Signal" : "Checkpoint"
);

const badgeVariant = computed(() => promotionActionBadgeVariant(props.promotion?.action));
const badgeText = computed(() => actionLabel.value);

const heroHint = computed(() => {
  const action = props.promotion?.action || "promote";
  const resource =
    props.promotion?.resource_type === "signal" ? "signal" : "checkpoint";
  const hints: Record<string, string> = {
    promote: `Version promotion recorded for this ${resource}.`,
    deactivate: `Live ${resource} version deactivated for this tenant.`,
    reactivate: `Previously inactive ${resource} version restored as current.`,
  };
  return hints[action] || `Governance action recorded for this ${resource}.`;
});

const flowLink = computed(() =>
  props.promotion?.resource_id
    ? routeWithTenant({
        name: "checkpoint-detail",
        params: { checkpointId: props.promotion.resource_id },
      })
    : routeWithTenant({ name: "checkpoints" })
);

const signalLink = computed(() =>
  props.promotion?.resource_id
    ? routeWithTenant({
        name: "signal-detail",
        params: { signalId: props.promotion.resource_id },
      })
    : routeWithTenant({ name: "signals" })
);

function formatTime(value?: string) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}
</script>
