<template>
  <div class="signals-view">
    <PageHeader
      title="Signal Library"
      subtitle="Configure connectors, functions, and variables for decision flows."
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
          <ResourceTable v-if="items.length">
            <template #table>
              <table class="resource-table">
                <thead>
                  <tr>
                    <th>Signal</th>
                    <th>Type</th>
                    <th>Cost</th>
                    <th>Status</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="s in items"
                    :key="s.id"
                    class="entity-table-row"
                    :class="{ selected: selectedId === s.id }"
                    @click="openSignal(s.id)"
                  >
                    <td>{{ s.name }}</td>
                    <td>
                      <StatusBadge :variant="badge(s.type)" :text="label(s.type)" />
                    </td>
                    <td>{{ s.cost ?? 0 }}</td>
                    <td>
                      <StatusBadge
                        :variant="s.is_current_version ? 'current' : 'inactive'"
                        :text="s.is_current_version ? 'Current' : 'Inactive'"
                      />
                      <StatusBadge
                        v-if="s.has_bearer_token"
                        variant="endpoint"
                        text="Secret"
                      />
                    </td>
                    <td @click.stop>
                      <button
                        v-if="!s.is_current_version"
                        type="button"
                        class="btn-secondary btn-sm"
                        @click="setCurrentVersion(s.id)"
                      >
                        Promote
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </template>
            <template #cards>
              <div
                v-for="s in items"
                :key="'card-' + s.id"
                class="resource-card card"
                :class="{ selected: selectedId === s.id }"
                @click="openSignal(s.id)"
              >
                <div class="resource-card-header">
                  <strong>{{ s.name }}</strong>
                  <StatusBadge :variant="badge(s.type)" :text="label(s.type)" />
                </div>
                <div class="resource-card-meta">
                  <StatusBadge
                    :variant="s.is_current_version ? 'current' : 'inactive'"
                    :text="s.is_current_version ? 'Current' : 'Inactive'"
                  />
                  <span class="text-muted">Cost {{ s.cost ?? 0 }}</span>
                </div>
                <div class="resource-card-actions" @click.stop>
                  <button
                    v-if="!s.is_current_version"
                    type="button"
                    class="btn-secondary btn-sm"
                    @click="setCurrentVersion(s.id)"
                  >
                    Promote
                  </button>
                  <button type="button" class="btn-ghost btn-sm" @click="openSignal(s.id)">
                    Open
                  </button>
                </div>
              </div>
            </template>
          </ResourceTable>
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
            <button type="button" class="btn-ghost btn-sm" @click="closePanel">Close</button>
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
              <FormSection title="Used by decision flows">
                <AssociationPicker
                  :linked-items="linkedFlows"
                  :candidates="checkpointCandidatesForSelected"
                  :search-query="checkpointSearchForSelected"
                  :page="checkpointPageForSelected"
                  :total-pages="checkpointTotalPagesForSelected"
                  :show-type="false"
                  empty-message="Not linked to any decision flows."
                  search-placeholder="Search flows to link…"
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
import * as formatters from "@/api/formatters";
import type { SignalDraft } from "@/api/types";
import { routeWithTenant } from "@/app/tenantNav";
import DataToolbar from "@/components/primitives/DataToolbar.vue";
import ResourceTable from "@/components/primitives/ResourceTable.vue";
import EmptyState from "@/components/primitives/EmptyState.vue";
import AppPagination from "@/components/primitives/AppPagination.vue";
import SignalDetails from "@/components/domain/signals/SignalDetails.vue";
import SignalForm from "@/components/domain/signals/SignalForm.vue";
import SignalVariablePanel from "@/components/domain/signals/SignalVariablePanel.vue";
import PageHeader from "@/components/workbench/PageHeader.vue";
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

const detailTabs = [
  { id: "summary", label: "Summary" },
  { id: "config", label: "Configuration" },
  { id: "associations", label: "Flows" },
  { id: "variables", label: "Values" },
];

const linkedFlows = computed(() =>
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

function badge(type: string) {
  return formatters.signalTypeBadge(type);
}

function label(type: string) {
  return formatters.signalTypeLabel(type);
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
