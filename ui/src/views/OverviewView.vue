<template>
  <div class="overview-view">
    <PageHeader title="Operations overview" subtitle="Tenant-scoped health and recent activity.">
      <template #actions>
        <button type="button" class="btn-secondary" @click="load">Refresh</button>
        <RouterLink class="btn-primary" :to="testDecisionsLink">Test Lab</RouterLink>
      </template>
    </PageHeader>

    <EmptyState
      v-if="!activeTenant"
      title="Select a tenant"
      message="Choose a tenant to see scoped flows, signals, and audit activity."
    />

    <LoadingSkeleton v-else-if="loading" block />

    <template v-else>
      <p v-if="error" class="inline-error">{{ error }}</p>

      <div class="stat-grid">
        <div class="card stat-card">
          <span class="stat-label">Active flows</span>
          <strong class="stat-value">{{ checkpointCount }}</strong>
        </div>
        <div class="card stat-card">
          <span class="stat-label">Active signals</span>
          <strong class="stat-value">{{ signalCount }}</strong>
        </div>
        <div class="card stat-card">
          <span class="stat-label">Recent decisions</span>
          <strong class="stat-value">{{ recentDecisionCount }}</strong>
        </div>
        <div class="card stat-card">
          <span class="stat-label">Signal failures</span>
          <strong class="stat-value">{{ failedSignalCount }}</strong>
        </div>
      </div>

      <div class="dashboard-panels">
        <section class="card">
          <div class="resource-card-header">
            <h4>Recent decisions</h4>
            <RouterLink class="btn-ghost btn-sm" :to="auditLink">View all</RouterLink>
          </div>
          <ul v-if="recentDecisions.length" class="simple-list">
            <li v-for="d in recentDecisions" :key="d.id">
              <RouterLink :to="decisionLink(d.id)">
                <strong>{{ d.final_decision_value }}</strong>
                <span class="text-muted">
                  · {{ d.checkpoint_name || "flow" }} · {{ d.applicant_id || "—" }}
                </span>
              </RouterLink>
            </li>
          </ul>
          <EmptyState
            v-else
            title="No recent decisions"
            message="Run a test decision to populate audit history."
          />
        </section>

        <section class="card">
          <div class="resource-card-header">
            <h4>Failed signal calls</h4>
            <RouterLink class="btn-ghost btn-sm" :to="signalAuditLink">Triage</RouterLink>
          </div>
          <ul v-if="failedSignalLogs.length" class="simple-list">
            <li v-for="log in failedSignalLogs" :key="log.id">
              <strong>{{ log.signal_name || "signal" }}</strong>
              <span class="text-muted"> · {{ log.started_at || "—" }}</span>
            </li>
          </ul>
          <EmptyState
            v-else
            title="No failed signal logs"
            message="Failed invocations will appear here."
          />
        </section>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { storeToRefs } from "pinia";
import { RouterLink } from "vue-router";
import { routeWithTenant } from "@/app/tenantNav";
import EmptyState from "@/components/primitives/EmptyState.vue";
import PageHeader from "@/components/workbench/PageHeader.vue";
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
  recentDecisionCount,
  failedSignalCount,
  recentDecisions,
  failedSignalLogs,
} = storeToRefs(overview);

const { activeTenant } = storeToRefs(tenantStore);
const { load } = overview;

const testDecisionsLink = computed(() => routeWithTenant({ name: "test-decisions" }));
const auditLink = computed(() => routeWithTenant({ name: "audit-decisions" }));
const signalAuditLink = computed(() => routeWithTenant({ name: "audit-signal-logs" }));

function decisionLink(id: string) {
  return routeWithTenant({ name: "audit-decisions", query: { decision: id } });
}
</script>
