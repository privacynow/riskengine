<template>
  <div class="tenants-view">
    <PageHeader
      title="Tenants"
      subtitle="Create tenants, set the active workspace, and manage isolation boundaries."
    />

    <DataToolbar>
      <input
        v-model="searchTerm"
        type="search"
        placeholder="Search tenants"
        class="toolbar-grow"
      />
      <button type="button" class="btn-secondary" @click="search(1)">Search</button>
      <button type="button" class="btn-secondary" @click="fetchPage(1)">Load all</button>
      <button type="button" class="btn-primary" @click="toggleCreateForm">
        {{ showCreateForm ? "Close" : "Create tenant" }}
      </button>
    </DataToolbar>

    <div v-if="showCreateForm" class="card">
      <div class="form-field">
        <label>Name</label>
        <input v-model="newTenantName" type="text" />
      </div>
      <div class="form-field">
        <label>Copy from tenant ID (optional)</label>
        <input v-model="copyFromTenantId" type="text" />
      </div>
      <div class="form-actions">
        <button type="button" class="btn-primary" @click="createTenant">Create</button>
      </div>
    </div>

    <ResourceTable v-if="tenants.length">
      <template #table>
        <table class="resource-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Active</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <template v-for="t in tenants" :key="t.id">
              <tr>
                <td>{{ t.name }}</td>
                <td>
                  <button
                    type="button"
                    class="version-badge"
                    :class="activeTenant?.id === t.id ? 'current' : 'not-current'"
                    @click="setActiveTenant(activeTenant?.id === t.id ? null : t)"
                  >
                    {{ activeTenant?.id === t.id ? "✔" : "☆" }}
                  </button>
                </td>
                <td>
                  <button type="button" class="btn-ghost btn-sm" @click="toggleExpand(t.id)">
                    {{ expanded[t.id] ? "Hide" : "Edit" }}
                  </button>
                </td>
              </tr>
              <tr v-if="expanded[t.id]">
                <td colspan="3">
                  <div class="expandable-panel card">
                    <div class="form-field">
                      <label>Name</label>
                      <input v-model="edits[t.id].name" type="text" />
                    </div>
                    <div class="form-actions">
                      <button type="button" class="btn-primary btn-sm" @click="saveTenant(t.id)">
                        Save
                      </button>
                    </div>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </template>
      <template #cards>
        <div v-for="t in tenants" :key="'card-' + t.id" class="resource-card card">
          <div class="resource-card-header">
            <strong>{{ t.name }}</strong>
            <button
              type="button"
              class="version-badge"
              :class="activeTenant?.id === t.id ? 'current' : 'not-current'"
              @click="setActiveTenant(activeTenant?.id === t.id ? null : t)"
            >
              {{ activeTenant?.id === t.id ? "Active" : "Set active" }}
            </button>
          </div>
          <div class="resource-card-actions">
            <button type="button" class="btn-ghost btn-sm" @click="toggleExpand(t.id)">
              {{ expanded[t.id] ? "Hide" : "Edit" }}
            </button>
          </div>
          <div v-if="expanded[t.id]" class="expandable-panel">
            <div class="form-field">
              <label>Name</label>
              <input v-model="edits[t.id].name" type="text" />
            </div>
            <div class="form-actions">
              <button type="button" class="btn-primary btn-sm" @click="saveTenant(t.id)">
                Save
              </button>
            </div>
          </div>
        </div>
      </template>
    </ResourceTable>

    <EmptyState v-else title="No tenants" message="Create a tenant to get started." />

    <AppPagination
      :page="page"
      :total-pages="totalPages"
      @prev="fetchPage(page - 1)"
      @next="fetchPage(page + 1)"
    />
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from "pinia";
import DataToolbar from "@/components/primitives/DataToolbar.vue";
import ResourceTable from "@/components/primitives/ResourceTable.vue";
import EmptyState from "@/components/primitives/EmptyState.vue";
import AppPagination from "@/components/primitives/AppPagination.vue";
import PageHeader from "@/components/workbench/PageHeader.vue";
import { useTenantStore } from "@/stores/tenantStore";

const store = useTenantStore();
const {
  searchTerm,
  newTenantName,
  showCreateForm,
  copyFromTenantId,
  tenants,
  page,
  totalPages,
  expanded,
  edits,
  activeTenant,
} = storeToRefs(store);
const { search, fetchPage, toggleCreateForm, createTenant, toggleExpand, saveTenant, setActiveTenant } =
  store;
</script>
