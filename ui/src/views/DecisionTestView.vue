<template>
  <div class="decision-test-view">
    <PageHeader
      title="Test Lab"
      subtitle="Run decision scenarios and inspect per-signal execution."
    />

    <DataToolbar>
      <input
        v-model="searchTerm"
        type="search"
        placeholder="Search decision flows"
        class="toolbar-grow"
      />
      <button type="button" class="btn-secondary" @click="search(1)">Search</button>
      <button type="button" class="btn-secondary" @click="loadAll(1)">Load all</button>
    </DataToolbar>

    <EmptyState
      v-if="!activeTenant"
      title="Select a tenant"
      message="Use the tenant bar above to run test decisions."
    />

    <EmptyState
      v-else-if="!checkpoints.length"
      title="No decision flows loaded"
      message="Search flows, select one, and run a test."
    />

    <WorkbenchLayout v-else :split="!!selectedCheckpointId">
      <template #master>
        <ResourceTable>
          <template #table>
            <table class="resource-table">
              <thead>
                <tr>
                  <th>Flow</th>
                  <th>Type</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="cp in checkpoints"
                  :key="cp.id"
                  class="entity-table-row"
                  :class="{ selected: selectedCheckpointId === cp.id }"
                  @click="selectCheckpoint(cp.id)"
                >
                  <td>{{ cp.name }}</td>
                  <td>{{ cp.type || "—" }}</td>
                </tr>
              </tbody>
            </table>
          </template>
          <template #cards>
            <div
              v-for="cp in checkpoints"
              :key="'card-' + cp.id"
              class="resource-card card"
              :class="{ selected: selectedCheckpointId === cp.id }"
              @click="selectCheckpoint(cp.id)"
            >
              <strong>{{ cp.name }}</strong>
              <span class="text-muted">{{ cp.type }}</span>
            </div>
          </template>
        </ResourceTable>

        <AppPagination
          :page="page"
          :total-pages="totalPages"
          @prev="goToPage(page - 1)"
          @next="goToPage(page + 1)"
        />
      </template>

      <template v-if="activeCheckpoint" #detail>
        <div class="workbench-detail-header">
          <div>
            <h3>{{ activeCheckpoint.name }}</h3>
            <p class="field-hint">DSL: {{ activeCheckpoint.dsl_expression }}</p>
          </div>
        </div>
        <div class="workbench-detail-body">
          <FieldRow :columns="2">
            <div class="form-field">
              <label>Applicant ID</label>
              <input v-model="applicantIds[activeCheckpoint.id]" type="text" />
            </div>
            <div class="form-field">
              <label>Correlation ID</label>
              <input v-model="correlationIds[activeCheckpoint.id]" type="text" />
            </div>
          </FieldRow>

          <button type="button" class="btn-ghost btn-sm" @click="toggleExpand(activeCheckpoint.id)">
            {{ expanded[activeCheckpoint.id] ? "Hide parameters" : "Configure parameters" }}
          </button>

          <div v-if="expanded[activeCheckpoint.id]" class="expandable-panel">
            <div
              v-for="sig in assocSignals[activeCheckpoint.id] || []"
              :key="sig.id"
              class="signal-param-block"
            >
              <strong>{{ sig.name }}</strong>
              <div v-for="ph in sig.param_placeholders || []" :key="ph" class="form-field">
                <label>{{ ph }}</label>
                <input v-model="params[activeCheckpoint.id][sig.id][ph]" type="text" />
              </div>
            </div>
          </div>

          <div class="form-actions">
            <button type="button" class="btn-primary" :disabled="running" @click="invoke(activeCheckpoint.id)">
              {{ running ? "Running…" : "Run test" }}
            </button>
          </div>

          <DecisionResultPanel :result="responses[activeCheckpoint.id] || null" />
        </div>
      </template>
    </WorkbenchLayout>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { storeToRefs } from "pinia";
import DataToolbar from "@/components/primitives/DataToolbar.vue";
import EmptyState from "@/components/primitives/EmptyState.vue";
import AppPagination from "@/components/primitives/AppPagination.vue";
import ResourceTable from "@/components/primitives/ResourceTable.vue";
import PageHeader from "@/components/workbench/PageHeader.vue";
import WorkbenchLayout from "@/components/workbench/WorkbenchLayout.vue";
import FieldRow from "@/components/workbench/FieldRow.vue";
import DecisionResultPanel from "@/components/workbench/DecisionResultPanel.vue";
import { useDecisionTestStore } from "@/stores/decisionTestStore";
import { useTenantStore } from "@/stores/tenantStore";

const testStore = useDecisionTestStore();
const tenantStore = useTenantStore();

const {
  searchTerm,
  checkpoints,
  page,
  totalPages,
  expanded,
  applicantIds,
  correlationIds,
  assocSignals,
  params,
  responses,
  selectedCheckpointId,
  running,
} = storeToRefs(testStore);

const { activeTenant } = storeToRefs(tenantStore);

const activeCheckpoint = computed(() =>
  checkpoints.value.find((cp) => cp.id === selectedCheckpointId.value)
);

const { loadAll, search, toggleExpand, invoke, selectCheckpoint } = testStore;

function goToPage(p: number) {
  if (searchTerm.value.trim()) search(p);
  else loadAll(p);
}
</script>
