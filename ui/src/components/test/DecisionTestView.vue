<template>
  <div class="decision-test-view">
    <data-toolbar>
      <input
        v-model="$root.testDecCheckpointSearchTerm"
        type="search"
        placeholder="Search checkpoints to test"
        class="toolbar-grow"
      />
      <button type="button" class="btn-secondary" @click="$root.searchTestDecCheckpoints(1)">Search</button>
      <button type="button" class="btn-secondary" @click="$root.loadAllTestDecCheckpoints(1)">Load all</button>
    </data-toolbar>

    <empty-state
      v-if="!$root.testDecCheckpoints.length"
      title="No checkpoints loaded"
      message="Search checkpoints, then run a test decision."
    ></empty-state>

    <div v-for="cp in $root.testDecCheckpoints" :key="cp.id" class="card test-card">
      <div class="resource-card-header">
        <strong>{{ cp.name }}</strong>
        <span class="text-muted">{{ cp.type }}</span>
      </div>
      <pre class="code-block">{{ cp.dsl_expression }}</pre>

      <div class="form-field">
        <label>Applicant ID</label>
        <input v-model="$root.testDecApplicantIds[cp.id]" type="text" />
      </div>
      <div class="form-field">
        <label>Correlation ID</label>
        <input v-model="$root.testDecCorrelationIds[cp.id]" type="text" />
      </div>

      <button type="button" class="btn-ghost btn-sm" @click="$root.toggleExpandTestDecCheckpoint(cp.id)">
        {{ $root.expandedTestDecCheckpoints[cp.id] ? "Hide signals" : "Configure signals" }}
      </button>

      <div v-if="$root.expandedTestDecCheckpoints[cp.id]" class="expandable-panel">
        <div
          v-for="sig in ($root.testDecAssocSignals[cp.id] || [])"
          :key="sig.id"
          class="signal-param-block"
        >
          <strong>{{ sig.name }}</strong>
          <div v-for="ph in sig.param_placeholders || []" :key="ph" class="form-field">
            <label>{{ ph }}</label>
            <input
              v-model="$root.testDecParams[cp.id][sig.id][ph]"
              type="text"
            />
          </div>
        </div>
      </div>

      <div class="form-actions">
        <button type="button" class="btn-primary" @click="$root.invokeTestDecision(cp.id)">Run test</button>
      </div>

      <div v-if="$root.testDecResponses[cp.id]" class="test-result">
        <h4>Result</h4>
        <pre class="code-block">{{ formatResult($root.testDecResponses[cp.id]) }}</pre>
      </div>
    </div>

    <app-pagination
      :page="$root.testDecCheckpointPage"
      :total-pages="$root.testDecCheckpointTotalPages"
      @prev="$root.prevTestDecCheckpointPage()"
      @next="$root.nextTestDecCheckpointPage()"
    ></app-pagination>
  </div>
</template>

<script>
import DataToolbar from "@/components/common/DataToolbar.vue";
import EmptyState from "@/components/common/EmptyState.vue";
import AppPagination from "@/components/common/Pagination.vue";

export default {
  components: { DataToolbar, EmptyState, AppPagination },
  name: "DecisionTestView",
  methods: {
    formatResult: function (result) {
      try {
        return JSON.stringify(result, null, 2);
      } catch (e) {
        return String(result);
      }
    },
  },
};
</script>
