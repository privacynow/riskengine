<template>
  <div v-if="log" class="signal-log-detail-panel">
    <div class="result-summary">
      <div class="result-metric">
        <div class="result-metric-label">Signal</div>
        <div class="result-metric-value">{{ log.signal_name || log.signal_id || "—" }}</div>
      </div>
      <div class="result-metric">
        <div class="result-metric-label">Value</div>
        <div class="result-metric-value">{{ log.signal_value ?? "—" }}</div>
      </div>
      <div class="result-metric">
        <div class="result-metric-label">Status</div>
        <div class="result-metric-value">{{ log.success === false ? "Failed" : "OK" }}</div>
      </div>
    </div>

    <dl class="detail-list">
      <div><dt>Applicant</dt><dd>{{ log.applicant_id || "—" }}</dd></div>
      <div><dt>Cost</dt><dd>{{ log.cost_incurred ?? "—" }}</dd></div>
      <div><dt>Started</dt><dd>{{ log.started_at || "—" }}</dd></div>
      <div><dt>Completed</dt><dd>{{ log.completed_at || "—" }}</dd></div>
    </dl>

    <FormSection v-if="log.param_values?.length" title="Parameters (redacted)">
      <ul class="simple-list">
        <li v-for="param in log.param_values" :key="param.param_name">
          <strong>{{ param.param_name }}</strong>: {{ param.param_value ?? "—" }}
        </li>
      </ul>
    </FormSection>

    <div class="form-actions">
      <RouterLink
        v-if="log.signal_id"
        class="btn-secondary btn-sm"
        :to="signalLink"
      >
        Open signal
      </RouterLink>
      <RouterLink
        v-if="log.decision_log_id"
        class="btn-primary btn-sm"
        :to="auditDecisionLink"
      >
        View decision
      </RouterLink>
    </div>

    <JsonInspector :data="log" summary="Raw signal log" />
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { RouterLink } from "vue-router";
import type { SignalLogSummary } from "@/api/types";
import { routeWithTenant } from "@/app/tenantNav";
import FormSection from "@/components/workbench/FormSection.vue";
import JsonInspector from "@/components/workbench/JsonInspector.vue";

const props = defineProps<{
  log: SignalLogSummary | null;
}>();

const signalLink = computed(() =>
  props.log?.signal_id
    ? routeWithTenant({ name: "signal-detail", params: { signalId: props.log.signal_id } })
    : routeWithTenant({ name: "signals" })
);

const auditDecisionLink = computed(() =>
  routeWithTenant({ name: "audit-decisions", query: { decision: props.log?.decision_log_id || "" } })
);
</script>
