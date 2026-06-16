<template>
  <header class="top-bar">
    <div class="top-bar-start">
      <button
        type="button"
        class="top-bar-menu-toggle"
        aria-label="Open navigation"
        @click="$root.mobileNavOpen = !$root.mobileNavOpen"
      >
        ☰
      </button>
      <div class="top-bar-titles">
        <h2 class="top-bar-title">{{ title }}</h2>
        <p class="page-header-subtitle">{{ subtitle }}</p>
      </div>
    </div>
    <div class="top-bar-end">
      <span class="session-status">Session active</span>
      <button type="button" class="btn-secondary btn-sm" @click="$root.clearAuthToken()">
        Sign out
      </button>
    </div>
  </header>
</template>

<script>
export default {
  name: "TopBar",
  computed: {
    title: function () {
      var map = {
        overview: "Operations overview",
        tenants: "Tenants",
        checkpoints: "Checkpoints",
        signals: "Signals",
        associations: "Associations",
        audit: "Audit search",
        test: "Test decisions",
      };
      return map[this.$root.view] || "Decision Engine";
    },
    subtitle: function () {
      if (this.$root.currentGlobalTenant) {
        return "Tenant: " + this.$root.currentGlobalTenant.name;
      }
      return "Select a tenant to scope checkpoint and signal work";
    },
  },
};
</script>
