<template>
  <div class="tenant-context-bar">
    <label class="tenant-context-label" for="tenant-select">Tenant</label>
    <select id="tenant-select" class="tenant-select" v-model="selectedTenantId">
      <option value="">Select tenant…</option>
      <option v-for="t in $root.allTenants" :key="t.id" :value="t.id">
        {{ t.name }}
      </option>
    </select>
    <span v-if="$root.currentGlobalTenant" class="badge badge-current">Active</span>
    <button
      v-if="$root.currentGlobalTenant"
      type="button"
      class="btn-ghost btn-sm"
      @click="$root.setCurrentTenant(null)"
    >
      Clear
    </button>
  </div>
</template>

<script>
export default {
  name: "TenantContext",
  computed: {
    selectedTenantId: {
      get: function () {
        return this.$root.currentGlobalTenant ? this.$root.currentGlobalTenant.id : "";
      },
      set: function (id) {
        if (!id) {
          this.$root.setCurrentTenant(null);
          return;
        }
        var tenant = this.$root.allTenants.find(function (t) {
          return t.id === id;
        });
        this.$root.setCurrentTenant(tenant || null);
        if (this.$root.view === "overview") {
          this.$root.loadDashboard();
        }
      },
    },
  },
};
</script>
