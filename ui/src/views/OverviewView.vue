<template>
  <div class="overview-view page-content-inner">
    <PageHeader title="Operations overview" subtitle="Tenant-scoped health and recent activity.">
      <template #actions>
        <button type="button" class="btn-secondary" @click="load">
          <Icon name="refresh" :size="14" />
          Refresh
        </button>
        <RouterLink class="btn-primary" :to="testDecisionsLink">Test Lab</RouterLink>
      </template>
    </PageHeader>

    <EmptyState
      v-if="!activeTenant"
      variant="panel"
      title="Select a tenant"
      message="Choose a tenant in the header to see scoped checkpoints, signals, and audit activity."
      icon="building"
    />

    <LoadingSkeleton v-else-if="loading" block />

    <div v-else class="overview-command-center">
      <p v-if="error" class="inline-error">{{ error }}</p>

      <QuickActionBar :actions="quickActions" />

      <div class="stat-grid overview-stat-grid">
        <StatCard
          label="Active checkpoints"
          :value="checkpointCount"
          icon="gitBranch"
          tone="primary"
          :hint="inactiveCheckpointCount ? `${inactiveCheckpointCount} inactive versions` : 'All versions current'"
        />
        <StatCard
          label="Active signals"
          :value="signalCount"
          icon="radio"
          tone="teal"
          :hint="inactiveSignalCount ? `${inactiveSignalCount} inactive versions` : 'All versions current'"
        />
        <StatCard
          label="Decision sample"
          :value="recentSampleCount"
          icon="activity"
          tone="default"
          :hint="recentSampleHint"
        />
        <StatCard
          label="Failed signal calls"
          :value="failedSignalCount"
          icon="alert"
          :tone="failedSignalCount ? 'danger' : 'success'"
          :hint="failedSignalCallsHint"
        />
        <StatCard
          label="Inactive versions"
          :value="staleVersionLabel"
          icon="layers"
          tone="warning"
          hint="Checkpoints and signals not on active version"
        />
        <StatCard
          label="Peak cost (sample)"
          :value="peakCostLabel"
          icon="dollar"
          :tone="costPressureTone"
          :hint="avgCostLabel !== '—' ? `Avg ${avgCostLabel} in sample · ${costPressureHint}` : costPressureHint"
        />
      </div>

      <div class="dashboard-panels overview-panels">
        <section class="card overview-panel-card">
          <PanelCardHeader title="Recent decisions">
            <template #actions>
              <RouterLink class="btn-ghost btn-sm" :to="auditLink">View all</RouterLink>
            </template>
          </PanelCardHeader>
          <div v-if="recentDecisions.length" class="list-row-stack">
            <DecisionListRow
              v-for="d in recentDecisions"
              :key="d.id"
              :decision="d"
              :to="decisionLink(d.id)"
            />
          </div>
          <div v-else class="overview-panel-empty">
            <EmptyState
              variant="panel"
              title="No recent decisions"
              message="Run a test decision to populate audit history."
              icon="flask"
            />
          </div>
        </section>

        <section class="card overview-panel-card">
          <PanelCardHeader title="Failed signal calls">
            <template #actions>
              <RouterLink class="btn-ghost btn-sm" :to="signalAuditLink">Triage</RouterLink>
            </template>
          </PanelCardHeader>
          <div v-if="failedSignalLogs.length" class="list-row-stack">
            <SignalLogListRow
              v-for="log in failedSignalLogs"
              :key="log.id"
              :log="log"
              :to="signalLogLink(log.id)"
            />
          </div>
          <div v-else class="overview-panel-empty">
            <EmptyState
              variant="panel"
              title="No failed signal logs"
              message="Failed invocations will appear here for triage."
              icon="radio"
            />
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { storeToRefs } from "pinia";
import { RouterLink } from "vue-router";
import { routeWithTenant } from "@/app/tenantNav";
import Icon from "@/components/primitives/Icon.vue";
import EmptyState from "@/components/primitives/EmptyState.vue";
import DecisionListRow from "@/components/overview/DecisionListRow.vue";
import SignalLogListRow from "@/components/overview/SignalLogListRow.vue";
import QuickActionBar from "@/components/overview/QuickActionBar.vue";
import StatCard from "@/components/overview/StatCard.vue";
import PageHeader from "@/components/workbench/PageHeader.vue";
import PanelCardHeader from "@/components/workbench/PanelCardHeader.vue";
import LoadingSkeleton from "@/components/workbench/LoadingSkeleton.vue";
import { useOverviewStore } from "@/stores/overviewStore";
import { useTenantStore } from "@/stores/tenantStore";

const overview = useOverviewStore();
const tenantStore = useTenantStore();

const {
  loading,
  error,
  checkpointCount,
  signalCount,
  inactiveCheckpointCount,
  inactiveSignalCount,
  failedSignalCount,
  recentDecisions,
  failedSignalLogs,
  recentSampleCount,
  recentSampleHint,
  failedSignalCallsHint,
  staleVersionLabel,
  costPressureHint,
  peakCostLabel,
  avgCostLabel,
  costPressureTone,
} = storeToRefs(overview);

const { activeTenant } = storeToRefs(tenantStore);
const { load } = overview;

const testDecisionsLink = computed(() => routeWithTenant({ name: "test-decisions" }));
const auditLink = computed(() => routeWithTenant({ name: "audit-decisions" }));
const signalAuditLink = computed(() => routeWithTenant({ name: "audit-signal-logs" }));
const flowsLink = computed(() => routeWithTenant({ name: "checkpoints" }));
const signalsLink = computed(() => routeWithTenant({ name: "signals" }));

const quickActions = computed(() => [
  {
    label: "Run test",
    hint: "Exercise a checkpoint",
    icon: "flask" as const,
    to: testDecisionsLink.value,
  },
  {
    label: "Triage failures",
    hint: "Signal audit log",
    icon: "alert" as const,
    to: signalAuditLink.value,
  },
  {
    label: "New checkpoint",
    hint: "Checkpoints",
    icon: "plus" as const,
    to: flowsLink.value,
  },
  {
    label: "New signal",
    hint: "Signal library",
    icon: "zap" as const,
    to: signalsLink.value,
  },
]);

function decisionLink(id: string) {
  return routeWithTenant({ name: "audit-decisions", query: { decision: id } });
}

function signalLogLink(id: string) {
  return routeWithTenant({ name: "audit-signal-logs", query: { signal_log: id } });
}
</script>
