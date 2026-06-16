<template>
  <div class="tenants-view">
    <data-toolbar>
      <input
        type="search"
        v-model="$root.tenantSearchTerm"
        placeholder="Search tenants"
        class="toolbar-grow"
      />
      <button type="button" class="btn-secondary" @click="$root.searchTenants(1)">Search</button>
      <button type="button" class="btn-secondary" @click="$root.fetchTenants(1)">Load all</button>
      <button type="button" class="btn-primary" @click="$root.toggleTenantCreateForm()">
        {{ $root.showTenantCreateForm ? "Close" : "Create tenant" }}
      </button>
    </data-toolbar>

    <div v-if="$root.showTenantCreateForm" class="card">
      <div class="form-field">
        <label>Name</label>
        <input v-model="$root.newTenantName" type="text" />
      </div>
      <div class="form-field">
        <label>Copy from tenant ID (optional)</label>
        <input v-model="$root.copyFromTenantId" type="text" />
      </div>
      <div class="form-actions">
        <button type="button" class="btn-primary" @click="$root.createTenant()">Create</button>
      </div>
    </div>

    <resource-table v-if="$root.tenants.length">
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
          <template v-for="t in $root.tenants" :key="t.id">
              <tr>
              <td>{{ t.name }}</td>
              <td>
                <button
                  type="button"
                  class="version-badge"
                  :class="$root.currentGlobalTenant && $root.currentGlobalTenant.id === t.id ? 'current' : 'not-current'"
                  @click="$root.setCurrentTenant($root.currentGlobalTenant && $root.currentGlobalTenant.id === t.id ? null : t)"
                >
                  {{ $root.currentGlobalTenant && $root.currentGlobalTenant.id === t.id ? "✔" : "☆" }}
                </button>
              </td>
              <td>
                <button type="button" class="btn-ghost btn-sm" @click="$root.toggleExpandTenant(t.id)">
                  {{ $root.expandedTenants[t.id] ? "Hide" : "Edit" }}
                </button>
              </td>
            </tr>
            <tr v-if="$root.expandedTenants[t.id]">
              <td colspan="3">
                <div class="expandable-panel card">
                  <div class="form-field">
                    <label>Name</label>
                    <input v-model="$root.tenantEdits[t.id].name" type="text" />
                  </div>
                  <div class="form-actions">
                    <button type="button" class="btn-primary btn-sm" @click="$root.saveTenant(t.id)">Save</button>
                  </div>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
        </template>
        <template #cards>
        <div v-for="t in $root.tenants" :key="'card-' + t.id" class="resource-card card">
          <div class="resource-card-header">
            <strong>{{ t.name }}</strong>
            <button
              type="button"
              class="btn-ghost btn-sm"
              @click="$root.setCurrentTenant($root.currentGlobalTenant && $root.currentGlobalTenant.id === t.id ? null : t)"
            >
              {{ $root.currentGlobalTenant && $root.currentGlobalTenant.id === t.id ? "Active" : "Set active" }}
            </button>
          </div>
          <button type="button" class="btn-secondary btn-sm" @click="$root.toggleExpandTenant(t.id)">
            {{ $root.expandedTenants[t.id] ? "Hide" : "Edit" }}
          </button>
          <div v-if="$root.expandedTenants[t.id]" class="expandable-panel">
            <input v-model="$root.tenantEdits[t.id].name" type="text" />
            <button type="button" class="btn-primary btn-sm" @click="$root.saveTenant(t.id)">Save</button>
          </div>
        </div>
      
        </template>
      </resource-table>

    <empty-state v-else title="No tenants" message="Create a tenant to get started." ></empty-state>

    <app-pagination
      :page="$root.tenantPage"
      :total-pages="$root.tenantTotalPages"
      @prev="$root.prevTenantPage()"
      @next="$root.nextTenantPage()"
    ></app-pagination>
  </div>
</template>

<script>
import DataToolbar from "@/components/common/DataToolbar.vue";
import ResourceTable from "@/components/common/ResourceTable.vue";
import EmptyState from "@/components/common/EmptyState.vue";
import AppPagination from "@/components/common/Pagination.vue";

export default {
  components: { DataToolbar, ResourceTable, EmptyState, AppPagination },
  name: "TenantsView",
  mounted: function () {
    this.$root.fetchTenants(this.$root.tenantPage || 1);
  },
};
</script>
