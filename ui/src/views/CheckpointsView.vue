<template>
  <div class="checkpoints-view">
    <PageHeader
      title="Checkpoints"
      subtitle="Design checkpoints, wire signals, and manage versions."
    />

    <DataToolbar>
      <select v-model="activeFilter" class="toolbar-select">
        <option value="active">Active only</option>
        <option value="all">All checkpoints</option>
      </select>
      <input
        v-model="searchTerm"
        type="search"
        placeholder="Search checkpoints"
        class="toolbar-grow"
      />
      <button type="button" class="btn-secondary" @click="search(1)">Search</button>
      <button type="button" class="btn-secondary" @click="loadAll(1)">Load all</button>
      <button type="button" class="btn-primary" @click="toggleCreateForm">
        {{ showCreateForm ? "Close" : "New checkpoint" }}
      </button>
    </DataToolbar>

    <EmptyState
      v-if="!activeTenant"
      title="Select a tenant"
      message="Use the tenant bar above to scope checkpoints."
    />

    <div v-else>
      <div v-if="showCreateForm" class="card workbench-create-panel">
        <CheckpointForm
          v-model="draft"
          :create-new="true"
          @save="onCreateSave"
          @cancel="showCreateForm = false"
          @add-signal="addSignalToDraft"
          @remove-signal="removeSignalFromDraft"
          @search-signals="onCreateSignalSearch"
          @load-all-signals="loadDraftSignals(1)"
          @signal-page-change="loadDraftSignals"
        />
      </div>

      <LoadingSkeleton v-if="loading" block />

      <WorkbenchLayout v-else :split="!!selectedId">
        <template #master>
          <div v-if="items.length" class="card workbench-list-card">
            <div class="list-row-stack">
              <CheckpointListRow
                v-for="cp in items"
                :key="cp.id"
                :checkpoint="cp"
                :selected="selectedId === cp.id"
                @open="openCheckpoint(cp.id)"
                @promote="setCurrentVersion(cp.id)"
                @deactivate="deactivateVersion(cp.id)"
                @reactivate="reactivateVersion(cp.id)"
              />
            </div>
          </div>
          <EmptyState v-else title="No checkpoints" message="Create a checkpoint for this tenant." />

          <AppPagination
            :page="page"
            :total-pages="totalPages"
            @prev="goToPage(page - 1)"
            @next="goToPage(page + 1)"
          />
        </template>

        <template v-if="selectedCheckpoint" #detail>
          <div class="workbench-detail-header">
            <div>
              <h3>{{ selectedCheckpoint.name }}</h3>
              <StatusBadge
                :variant="selectedCheckpoint.is_current_version ? 'current' : 'inactive'"
                :text="
                  selectedCheckpoint.is_current_version ? 'Current version' : 'Inactive version'
                "
              />
            </div>
            <div class="workbench-detail-actions">
              <button
                v-if="selectedCheckpoint.is_current_version"
                type="button"
                class="btn-secondary btn-sm"
                @click="deactivateVersion(selectedCheckpoint.id)"
              >
                Deactivate
              </button>
              <button
                v-else-if="canPromoteSelected"
                type="button"
                class="btn-secondary btn-sm"
                @click="setCurrentVersion(selectedCheckpoint.id)"
              >
                Promote
              </button>
              <button
                v-else-if="canReactivateSelected"
                type="button"
                class="btn-secondary btn-sm"
                @click="reactivateVersion(selectedCheckpoint.id)"
              >
                Reactivate
              </button>
              <button type="button" class="btn-ghost btn-sm" @click="closePanel">Close</button>
            </div>
          </div>

          <WorkbenchTabs v-model="detailTab" :tabs="detailTabs" />

          <div class="workbench-detail-body">
            <div v-if="detailTab === 'summary'" class="detail-section">
              <dl class="detail-list">
                <div><dt>Type</dt><dd>{{ selectedCheckpoint.type || "—" }}</dd></div>
                <div><dt>Description</dt><dd>{{ selectedCheckpoint.description || "—" }}</dd></div>
                <div><dt>Max cost</dt><dd>{{ selectedCheckpoint.max_cost ?? 0 }}</dd></div>
                <div><dt>Timeout</dt><dd>{{ selectedCheckpoint.timeout_seconds ?? 30 }}s</dd></div>
              </dl>
              <pre class="code-block">{{ selectedCheckpoint.dsl_expression }}</pre>
            </div>

            <CheckpointForm
              v-else-if="detailTab === 'config'"
              v-model="detailDraft"
              :show-signals="false"
              @save="onDetailSave"
              @cancel="resetDetailDraft"
            />

            <CheckpointForm
              v-else-if="detailTab === 'signals'"
              v-model="detailDraft"
              :show-signals="true"
              @save="onSignalsSave"
              @cancel="resetDetailDraft"
              @add-signal="addSignalToDetail"
              @remove-signal="removeSignalFromDetail"
              @search-signals="onDetailSignalSearch"
              @load-all-signals="searchSignalsForDetail(1)"
              @signal-page-change="searchSignalsForDetail"
            />
          </div>
        </template>
      </WorkbenchLayout>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { storeToRefs } from "pinia";
import type { CheckpointDraft } from "@/api/types";
import { canPromoteVersion, canReactivateVersion } from "@/api/formatters";
import { routeWithTenant } from "@/app/tenantNav";
import DataToolbar from "@/components/primitives/DataToolbar.vue";
import EmptyState from "@/components/primitives/EmptyState.vue";
import AppPagination from "@/components/primitives/AppPagination.vue";
import CheckpointForm from "@/components/domain/checkpoints/CheckpointForm.vue";
import PageHeader from "@/components/workbench/PageHeader.vue";
import CheckpointListRow from "@/components/workbench/CheckpointListRow.vue";
import WorkbenchLayout from "@/components/workbench/WorkbenchLayout.vue";
import WorkbenchTabs from "@/components/workbench/WorkbenchTabs.vue";
import StatusBadge from "@/components/workbench/StatusBadge.vue";
import LoadingSkeleton from "@/components/workbench/LoadingSkeleton.vue";
import { useCheckpointStore } from "@/stores/checkpointStore";
import { useTenantStore } from "@/stores/tenantStore";

const route = useRoute();
const router = useRouter();
const checkpointStore = useCheckpointStore();
const tenantStore = useTenantStore();

const {
  draft,
  showCreateForm,
  items,
  searchTerm,
  activeFilter,
  page,
  totalPages,
  loading,
  selectedId,
  detailTab,
  detailDraft,
} = storeToRefs(checkpointStore);

const { activeTenant } = storeToRefs(tenantStore);

const selectedCheckpoint = computed(() => checkpointStore.selectedCheckpoint);
const canPromoteSelected = computed(() =>
  selectedCheckpoint.value ? canPromoteVersion(selectedCheckpoint.value) : false
);
const canReactivateSelected = computed(() =>
  selectedCheckpoint.value ? canReactivateVersion(selectedCheckpoint.value) : false
);

const detailTabs = [
  { id: "summary", label: "Summary" },
  { id: "config", label: "DSL & policy" },
  { id: "signals", label: "Signals" },
];

const {
  loadAll,
  search,
  toggleCreateForm,
  create,
  selectCheckpoint,
  closeDetail,
  saveDetail,
  persistDetailAssociations,
  setCurrentVersion,
  deactivateVersion,
  reactivateVersion,
  loadDraftSignals,
  addSignalToDraft,
  removeSignalFromDraft,
  searchSignalsForDetail,
  addSignalToDetail,
  removeSignalFromDetail,
} = checkpointStore;

watch(
  () => route.params.checkpointId,
  (id) => {
    const checkpointId = typeof id === "string" ? id : null;
    if (checkpointId && checkpointId !== selectedId.value) {
      selectCheckpoint(checkpointId);
    } else if (!checkpointId && selectedId.value) {
      closeDetail();
    }
  },
  { immediate: true }
);

function openCheckpoint(id: string) {
  router.push(routeWithTenant({ name: "checkpoint-detail", params: { checkpointId: id } }));
}

function closePanel() {
  router.push(routeWithTenant({ name: "checkpoints" }));
}

function resetDetailDraft() {
  if (selectedCheckpoint.value) selectCheckpoint(selectedCheckpoint.value.id);
}

function onDetailSignalSearch(query: string) {
  detailDraft.value.signalSearch = query;
  searchSignalsForDetail(1);
}

function goToPage(p: number) {
  if (searchTerm.value.trim()) search(p);
  else loadAll(p);
}

async function onCreateSave(value: CheckpointDraft) {
  draft.value = value;
  await create();
}

async function onDetailSave(value: CheckpointDraft) {
  detailDraft.value = value;
  await saveDetail();
}

async function onSignalsSave(value: CheckpointDraft) {
  detailDraft.value = value;
  await persistDetailAssociations();
}

function onCreateSignalSearch(query: string) {
  draft.value.signalSearch = query;
  loadDraftSignals(1);
}
</script>
