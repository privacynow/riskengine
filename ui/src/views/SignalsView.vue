<template>
  <div class="signals-view">
    <PageHeader
      title="Signal Library"
      subtitle="Configure connectors, functions, and variables for checkpoints."
    />

    <DataToolbar>
      <select v-model="activeFilter" class="toolbar-select">
        <option value="active">Active only</option>
        <option value="all">All signals</option>
      </select>
      <input
        v-model="searchTerm"
        type="search"
        placeholder="Search signals"
        class="toolbar-grow"
      />
      <button type="button" class="btn-secondary" @click="search(1)">Search</button>
      <button type="button" class="btn-secondary" @click="loadAll(1)">Load all</button>
      <button type="button" class="btn-primary" @click="toggleCreateForm">
        {{ showCreateForm ? "Close" : "New signal" }}
      </button>
    </DataToolbar>

    <EmptyState
      v-if="!activeTenant"
      title="Select a tenant"
      message="Use the tenant bar above to scope the signal library."
    />

    <div v-else>
      <div v-if="showCreateForm" class="card workbench-create-panel">
        <SignalForm v-model="draft" :create-new="true" @save="onCreateSave" @cancel="showCreateForm = false" />
      </div>

      <LoadingSkeleton v-if="loading" block />

      <WorkbenchLayout v-else :split="!!selectedId">
        <template #master>
          <div v-if="items.length" class="card workbench-list-card">
            <div class="list-row-stack">
              <SignalListRow
                v-for="s in items"
                :key="s.id"
                :signal="s"
                :selected="selectedId === s.id"
                @open="openSignal(s.id)"
                @promote="setCurrentVersion(s.id)"
                @deactivate="deactivateVersion(s.id)"
                @reactivate="reactivateVersion(s.id)"
              />
            </div>
          </div>
          <EmptyState v-else title="No signals" message="Create a signal for this tenant." />

          <AppPagination
            :page="page"
            :total-pages="totalPages"
            @prev="goToPage(page - 1)"
            @next="goToPage(page + 1)"
          />
        </template>

        <template v-if="selectedSignal" #detail>
          <div class="workbench-detail-header">
            <div>
              <h3>{{ selectedSignal.name }}</h3>
              <StatusBadge
                :variant="selectedSignal.is_current_version ? 'current' : 'inactive'"
                :text="selectedSignal.is_current_version ? 'Current version' : 'Inactive version'"
              />
            </div>
            <div class="workbench-detail-actions">
              <button
                v-if="selectedSignal.is_current_version"
                type="button"
                class="btn-secondary btn-sm"
                @click="deactivateVersion(selectedSignal.id)"
              >
                Deactivate
              </button>
              <button
                v-else-if="canPromoteSelected"
                type="button"
                class="btn-secondary btn-sm"
                @click="setCurrentVersion(selectedSignal.id)"
              >
                Promote
              </button>
              <button
                v-else-if="canReactivateSelected"
                type="button"
                class="btn-secondary btn-sm"
                @click="reactivateVersion(selectedSignal.id)"
              >
                Reactivate
              </button>
              <button type="button" class="btn-ghost btn-sm" @click="closePanel">Close</button>
            </div>
          </div>

          <WorkbenchTabs v-model="detailTab" :tabs="detailTabs" />

          <div class="workbench-detail-body">
            <SignalDetails v-if="detailTab === 'summary'" :signal="selectedSignal" />

            <SignalForm
              v-else-if="detailTab === 'config'"
              v-model="detailDraft"
              :has-bearer-token="selectedSignal.has_bearer_token"
              @save="onDetailSave"
              @cancel="resetDetailDraft"
            />

            <div v-else-if="detailTab === 'associations'">
              <FormSection title="Used by checkpoints">
                <AssociationPicker
                  :linked-items="linkedCheckpoints"
                  :candidates="checkpointCandidatesForSelected"
                  :search-query="checkpointSearchForSelected"
                  :page="checkpointPageForSelected"
                  :total-pages="checkpointTotalPagesForSelected"
                  :show-type="false"
                  empty-message="Not linked to any checkpoints."
                  search-placeholder="Search checkpoints to link…"
                  @remove="(id) => removeAssociation(selectedId!, id)"
                  @add="(id) => associateCheckpoint(selectedId!, id)"
                  @search="onCheckpointSearch"
                  @load-all="searchCheckpointsForEdit(selectedId!, 1)"
                  @page-change="(p) => searchCheckpointsForEdit(selectedId!, p)"
                />
              </FormSection>
            </div>

            <SignalVariablePanel
              v-else-if="detailTab === 'variables' && selectedSignal.type === 'variable'"
              :signal-id="selectedSignal.id"
            />
            <EmptyState
              v-else-if="detailTab === 'variables'"
              title="Not a variable signal"
              message="Variable values apply only to variable-type signals."
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
import type { SignalDraft } from "@/api/types";
import { canPromoteVersion, canReactivateVersion } from "@/api/formatters";
import { routeWithTenant } from "@/app/tenantNav";
import DataToolbar from "@/components/primitives/DataToolbar.vue";
import EmptyState from "@/components/primitives/EmptyState.vue";
import AppPagination from "@/components/primitives/AppPagination.vue";
import SignalDetails from "@/components/domain/signals/SignalDetails.vue";
import SignalForm from "@/components/domain/signals/SignalForm.vue";
import SignalVariablePanel from "@/components/domain/signals/SignalVariablePanel.vue";
import PageHeader from "@/components/workbench/PageHeader.vue";
import SignalListRow from "@/components/workbench/SignalListRow.vue";
import WorkbenchLayout from "@/components/workbench/WorkbenchLayout.vue";
import WorkbenchTabs from "@/components/workbench/WorkbenchTabs.vue";
import StatusBadge from "@/components/workbench/StatusBadge.vue";
import FormSection from "@/components/workbench/FormSection.vue";
import AssociationPicker from "@/components/workbench/AssociationPicker.vue";
import LoadingSkeleton from "@/components/workbench/LoadingSkeleton.vue";
import { useSignalStore } from "@/stores/signalStore";
import { useTenantStore } from "@/stores/tenantStore";

const route = useRoute();
const router = useRouter();
const signalStore = useSignalStore();
const tenantStore = useTenantStore();

const {
  items,
  draft,
  showCreateForm,
  searchTerm,
  activeFilter,
  page,
  totalPages,
  loading,
  selectedId,
  detailTab,
  detailDraft,
  detailAssociatedCheckpoints,
  checkpointSearch,
  checkpointCandidates,
  checkpointCandidatePage,
  checkpointCandidateTotalPages,
} = storeToRefs(signalStore);

const { activeTenant } = storeToRefs(tenantStore);

const selectedSignal = computed(() => signalStore.selectedSignal);
const canPromoteSelected = computed(() =>
  selectedSignal.value ? canPromoteVersion(selectedSignal.value) : false
);
const canReactivateSelected = computed(() =>
  selectedSignal.value ? canReactivateVersion(selectedSignal.value) : false
);

const detailTabs = [
  { id: "summary", label: "Summary" },
  { id: "config", label: "Configuration" },
  { id: "associations", label: "Checkpoints" },
  { id: "variables", label: "Values" },
];

const linkedCheckpoints = computed(() =>
  detailAssociatedCheckpoints.value.map((cp) => ({ id: cp.id, name: cp.name }))
);

const checkpointSearchForSelected = computed(() =>
  selectedId.value ? checkpointSearch.value[selectedId.value] || "" : ""
);

const checkpointPageForSelected = computed(() =>
  selectedId.value ? checkpointCandidatePage.value[selectedId.value] || 1 : 1
);

const checkpointTotalPagesForSelected = computed(() =>
  selectedId.value ? checkpointCandidateTotalPages.value[selectedId.value] || 1 : 1
);

const checkpointCandidatesForSelected = computed(() => {
  if (!selectedId.value) return [];
  return (checkpointCandidates.value[selectedId.value] || []).map((cp) => ({
    id: cp.id,
    name: cp.name,
  }));
});

const {
  loadAll,
  search,
  toggleCreateForm,
  create,
  selectSignal,
  closeDetail,
  saveDetail,
  setCurrentVersion,
  deactivateVersion,
  reactivateVersion,
  removeAssociation,
  associateCheckpoint,
  searchCheckpointsForEdit,
} = signalStore;

watch(
  () => route.params.signalId,
  (id) => {
    const signalId = typeof id === "string" ? id : null;
    if (signalId && signalId !== selectedId.value) {
      selectSignal(signalId);
    } else if (!signalId && selectedId.value) {
      closeDetail();
    }
  },
  { immediate: true }
);

function openSignal(id: string) {
  router.push(routeWithTenant({ name: "signal-detail", params: { signalId: id } }));
}

function closePanel() {
  router.push(routeWithTenant({ name: "signals" }));
}

function resetDetailDraft() {
  if (selectedSignal.value) selectSignal(selectedSignal.value.id);
}

function onCheckpointSearch(query: string) {
  if (!selectedId.value) return;
  checkpointSearch.value[selectedId.value] = query;
  searchCheckpointsForEdit(selectedId.value, 1);
}

function goToPage(p: number) {
  if (searchTerm.value.trim()) search(p);
  else loadAll(p);
}

async function onCreateSave(value: SignalDraft) {
  draft.value = value;
  await create();
}

async function onDetailSave(value: SignalDraft) {
  detailDraft.value = value;
  const newId = await saveDetail();
  if (newId && newId !== selectedId.value) {
    router.push(routeWithTenant({ name: "signal-detail", params: { signalId: newId } }));
  }
}
</script>
