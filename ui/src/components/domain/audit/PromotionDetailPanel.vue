<template>
  <div v-if="promotion" class="promotion-detail-panel audit-console">
    <div class="audit-outcome-hero audit-outcome-hero--neutral">
      <StatusBadge :variant="badgeVariant" :text="badgeText" />
      <div class="audit-outcome-hero-body">
        <h4>{{ promotion.resource_name }}</h4>
        <p class="field-hint">Version promotion recorded for this tenant.</p>
      </div>
      <div class="audit-outcome-hero-metric">
        <span class="result-metric-label">Actor</span>
        <span class="result-metric-value">{{ promotion.actor_id }}</span>
      </div>
    </div>

    <FormSection title="Promotion reason">
      <p class="promotion-reason-copy">{{ promotion.promotion_reason }}</p>
    </FormSection>

    <FormSection title="Resource context">
      <dl class="detail-list">
        <div><dt>Resource type</dt><dd>{{ promotion.resource_type }}</dd></div>
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
        Open flow
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
import { routeWithTenant } from "@/app/tenantNav";
import FormSection from "@/components/workbench/FormSection.vue";
import StatusBadge from "@/components/workbench/StatusBadge.vue";

const props = defineProps<{
  promotion: PromotionAuditSummary | null;
}>();

const badgeVariant = computed(() =>
  props.promotion?.resource_type === "signal" ? "inactive" : "current"
);
const badgeText = computed(() =>
  props.promotion?.resource_type === "signal" ? "Signal promoted" : "Flow promoted"
);

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
