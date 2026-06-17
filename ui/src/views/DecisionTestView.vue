<template>
  <div class="decision-test-view">
    <PageHeader
      title="Test Lab"
      subtitle="Controlled pre-promotion harness for checkpoints."
    />

    <DataToolbar>
      <input
        v-model="searchTerm"
        type="search"
        placeholder="Search checkpoints"
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

    <LoadingSkeleton v-else-if="loading" block />

    <EmptyState
      v-else-if="!checkpoints.length"
      title="No checkpoints loaded"
      message="Search checkpoints, select one, and run a test."
    />

    <WorkbenchLayout v-else :split="!!selectedCheckpointId">
      <template #master>
        <div class="card workbench-list-card">
          <div class="list-row-stack">
              <CheckpointListRow
                v-for="cp in checkpoints"
                :key="cp.id"
                :checkpoint="cp"
                :selected="selectedCheckpointId === cp.id"
                :promotable="false"
                @open="selectCheckpoint(cp.id)"
              />
          </div>
        </div>

        <AppPagination
          :page="page"
          :total-pages="totalPages"
          @prev="goToPage(page - 1)"
          @next="goToPage(page + 1)"
        />
      </template>

      <template v-if="activeCheckpoint" #detail>
        <div class="workbench-detail-body test-harness">
          <div class="test-harness-hero">
            <div class="test-harness-hero-main">
              <h3>{{ activeCheckpoint.name }}</h3>
              <div class="test-harness-hero-badges">
                <StatusBadge
                  :variant="activeCheckpoint.is_current_version ? 'current' : 'inactive'"
                  :text="activeCheckpoint.is_current_version ? 'Current version' : 'Draft version'"
                />
                <span v-if="activeCheckpoint.type" class="text-muted">{{ activeCheckpoint.type }}</span>
              </div>
              <p v-if="activeCheckpoint.description" class="field-hint">
                {{ activeCheckpoint.description }}
              </p>
            </div>
            <RouterLink
              class="btn-secondary btn-sm"
              :to="checkpointDetailLink"
            >
              Open checkpoint
            </RouterLink>
          </div>

          <FormSection title="DSL preflight" subtitle="Validate expression before promotion">
            <DslPreflightPanel
              :expression="activeCheckpoint.dsl_expression ?? ''"
              :checkpoint-id="activeCheckpoint.id"
            />
            <pre class="code-block code-block--compact">{{ activeCheckpoint.dsl_expression }}</pre>
          </FormSection>

          <FormSection title="Scenario inputs" subtitle="Fixture data for this test run">
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
              {{ expanded[activeCheckpoint.id] ? "Hide signal parameters" : "Configure signal parameters" }}
            </button>

            <div v-if="expanded[activeCheckpoint.id]" class="expandable-panel test-harness-params">
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
          </FormSection>

          <FormSection title="Run test">
            <p class="field-hint">
              Executes the selected checkpoint version server-side without promoting it live.
            </p>
            <div class="form-actions">
              <button
                type="button"
                class="btn-primary"
                :disabled="running"
                @click="invoke(activeCheckpoint.id)"
              >
                {{ running ? "Running…" : "Run test decision" }}
              </button>
            </div>
          </FormSection>

          <div v-if="responses[activeCheckpoint.id]" class="test-harness-result">
            <DecisionResultPanel
              :result="responses[activeCheckpoint.id] || null"
              variant="harness"
            />
          </div>
        </div>
      </template>
    </WorkbenchLayout>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { RouterLink } from "vue-router";
import { storeToRefs } from "pinia";
import { routeWithTenant } from "@/app/tenantNav";
import DataToolbar from "@/components/primitives/DataToolbar.vue";
import EmptyState from "@/components/primitives/EmptyState.vue";
import AppPagination from "@/components/primitives/AppPagination.vue";
import PageHeader from "@/components/workbench/PageHeader.vue";
import WorkbenchLayout from "@/components/workbench/WorkbenchLayout.vue";
import FieldRow from "@/components/workbench/FieldRow.vue";
import CheckpointListRow from "@/components/workbench/CheckpointListRow.vue";
import StatusBadge from "@/components/workbench/StatusBadge.vue";
import FormSection from "@/components/workbench/FormSection.vue";
import DslPreflightPanel from "@/components/workbench/DslPreflightPanel.vue";
import DecisionResultPanel from "@/components/workbench/DecisionResultPanel.vue";
import LoadingSkeleton from "@/components/workbench/LoadingSkeleton.vue";
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
  loading,
} = storeToRefs(testStore);

const { activeTenant } = storeToRefs(tenantStore);

const activeCheckpoint = computed(() =>
  checkpoints.value.find((cp) => cp.id === selectedCheckpointId.value)
);

const checkpointDetailLink = computed(() =>
  activeCheckpoint.value
    ? routeWithTenant({
        name: "checkpoint-detail",
        params: { checkpointId: activeCheckpoint.value.id },
      })
    : routeWithTenant({ name: "checkpoints" })
);

const { loadAll, search, toggleExpand, invoke, selectCheckpoint } = testStore;

function goToPage(p: number) {
  if (searchTerm.value.trim()) search(p);
  else loadAll(p);
}
</script>
