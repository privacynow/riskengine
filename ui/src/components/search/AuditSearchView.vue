<template>
  <div class="audit-search-view">
    <data-toolbar>
      <select v-model="$root.searchEntityType" class="toolbar-select">
        <option value="decisions">Decisions</option>
        <option value="signal_logs">Signal logs</option>
      </select>
      <input v-model="$root.searchQuery" type="search" placeholder="Search audit records" class="toolbar-grow" />
      <button type="button" class="btn-primary" @click="$root.doSearch(1)">Search</button>
    </data-toolbar>

    <div v-if="$root.searchEntityType === 'decisions'" class="card">
      <resource-table v-if="$root.searchDecisionsResults.length">
        <template #table>
        <table class="resource-table">
          <thead>
            <tr>
              <th>Decision</th>
              <th>Applicant</th>
              <th>Result</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <template v-for="res in $root.searchDecisionsResults" :key="res.id">
              <tr>
                <td class="mono">{{ res.id }}</td>
                <td>{{ res.applicant_id || "—" }}</td>
                <td>{{ res.final_decision_value }}</td>
                <td>
                  <button type="button" class="btn-ghost btn-sm" @click="$root.toggleExpandSearchDecision(res.id)">
                    {{ $root.expandedSearchDecisions[res.id] ? "Hide" : "Details" }}
                  </button>
                </td>
              </tr>
              <tr v-if="$root.expandedSearchDecisions[res.id]">
                <td colspan="4">
                  <pre class="code-block">{{ formatDecision($root.searchDecisionDetails[res.id]) }}</pre>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
        </template>
        <template #cards>
          <div v-for="res in $root.searchDecisionsResults" :key="'card-' + res.id" class="resource-card card">
            <strong>{{ res.final_decision_value }}</strong>
            <p class="text-muted">{{ res.applicant_id }}</p>
            <button type="button" class="btn-ghost btn-sm" @click="$root.toggleExpandSearchDecision(res.id)">Details</button>
          </div>
        
        </template>
      </resource-table>
      <empty-state v-else title="No decisions" message="Run a search to view decision audit records." ></empty-state>
      <app-pagination
        :page="$root.decisionSearchPage"
        :total-pages="$root.decisionSearchTotalPages"
        @prev="$root.decisionSearchPage > 1 && $root.doSearch($root.decisionSearchPage - 1)"
        @next="$root.decisionSearchPage < $root.decisionSearchTotalPages && $root.doSearch($root.decisionSearchPage + 1)"
      ></app-pagination>
    </div>

    <div v-else class="card">
      <resource-table v-if="$root.searchSignalLogsResults.length">
        <template #table>
        <table class="resource-table">
          <thead>
            <tr>
              <th>Signal value</th>
              <th>Applicant</th>
              <th>Success</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="res in $root.searchSignalLogsResults" :key="res.id">
              <td>{{ res.signal_value }}</td>
              <td>{{ res.applicant_id || "—" }}</td>
              <td>
                <app-badge :variant="res.success ? 'current' : 'inactive'" :text="res.success ? 'OK' : 'Failed'" ></app-badge>
              </td>
            </tr>
          </tbody>
        </table>
        </template>
        <template #cards>
          <div v-for="res in $root.searchSignalLogsResults" :key="'card-' + res.id" class="resource-card card">
            <strong>{{ res.signal_value }}</strong>
            <app-badge :variant="res.success ? 'current' : 'inactive'" :text="res.success ? 'OK' : 'Failed'" ></app-badge>
          </div>
        
        </template>
      </resource-table>
      <empty-state v-else title="No signal logs" message="Search signal execution logs." ></empty-state>
      <app-pagination
        :page="$root.signalLogsSearchPage"
        :total-pages="$root.signalLogsSearchTotalPages"
        @prev="$root.signalLogsSearchPage > 1 && $root.doSearch($root.signalLogsSearchPage - 1)"
        @next="$root.signalLogsSearchPage < $root.signalLogsSearchTotalPages && $root.doSearch($root.signalLogsSearchPage + 1)"
      ></app-pagination>
    </div>
  </div>
</template>

<script>
import * as formatters from "@/api/formatters.js";
import DataToolbar from "@/components/common/DataToolbar.vue";
import ResourceTable from "@/components/common/ResourceTable.vue";
import EmptyState from "@/components/common/EmptyState.vue";
import AppPagination from "@/components/common/Pagination.vue";
import AppBadge from "@/components/common/Badge.vue";

export default {
  components: { DataToolbar, ResourceTable, EmptyState, AppPagination, AppBadge },
  name: "AuditSearchView",
  methods: {
    formatDecision: function (detail) {
      if (!detail) return "Loading…";
      return formatters.formatJson(detail);
    },
  },
};
</script>
