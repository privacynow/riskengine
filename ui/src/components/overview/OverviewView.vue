<template>
  <div class="overview-view">
    <div class="page-header">
      <div>
        <h3>Operations overview</h3>
        <p class="text-muted">Tenant-scoped metrics and recent activity</p>
      </div>
      <div class="header-actions">
        <button type="button" class="btn-secondary" @click="$root.loadDashboard()">Refresh</button>
        <button type="button" class="btn-primary" @click="$root.switchView('test')">Run test</button>
      </div>
    </div>

    <p v-if="$root.dashboardLoading" class="text-muted">Loading dashboard…</p>
    <p v-else-if="$root.dashboardError" class="text-danger">{{ $root.dashboardError }}</p>

    <div v-else class="stat-grid">
      <div class="card stat-card">
        <span class="stat-label">Tenants</span>
        <strong class="stat-value">{{ $root.dashboardStats.tenantCount }}</strong>
      </div>
      <div class="card stat-card">
        <span class="stat-label">Active checkpoints</span>
        <strong class="stat-value">{{ $root.dashboardStats.checkpointCount }}</strong>
      </div>
      <div class="card stat-card">
        <span class="stat-label">Active signals</span>
        <strong class="stat-value">{{ $root.dashboardStats.signalCount }}</strong>
      </div>
    </div>

    <div class="dashboard-panels">
      <section class="card">
        <h4>Recent decisions</h4>
        <ul v-if="$root.dashboardStats.recentDecisions.length" class="simple-list">
          <li v-for="d in $root.dashboardStats.recentDecisions" :key="d.id">
            <strong>{{ d.final_decision_value }}</strong>
            <span class="text-muted"> · {{ d.applicant_id || "—" }}</span>
          </li>
        </ul>
        <empty-state v-else title="No recent decisions" message="Run a test decision to populate audit history." ></empty-state>
      </section>
      <section class="card">
        <h4>Failed signal calls</h4>
        <ul v-if="$root.dashboardStats.failedSignalLogs.length" class="simple-list">
          <li v-for="log in $root.dashboardStats.failedSignalLogs" :key="log.id">
            <strong>{{ log.signal_value || "failed" }}</strong>
            <span class="text-muted"> · {{ log.applicant_id || "—" }}</span>
          </li>
        </ul>
        <empty-state v-else title="No failed signal logs" message="Failed invocations will appear here." ></empty-state>
      </section>
    </div>

    <p class="text-muted help-link">
      DSL authoring reference: see <code>docs/DSL_GUIDE.md</code> in the repository.
    </p>
  </div>
</template>

<script>
import EmptyState from "@/components/common/EmptyState.vue";

export default {
  components: { EmptyState },
  name: "OverviewView",
  mounted: function () {
    this.$root.loadDashboard();
  },
};
</script>
