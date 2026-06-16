<template>
  <nav class="sidebar-nav" :class="{ open: $root.mobileNavOpen }">
    <button
      v-for="item in items"
      :key="item.id"
      type="button"
      class="nav-button"
      :class="{ active: $root.view === item.id }"
      @click="navigate(item.id)"
    >
      {{ item.label }}
    </button>
  </nav>
</template>

<script>
export default {
  name: "SidebarNav",
  data: function () {
    return {
      items: [
        { id: "overview", label: "Overview" },
        { id: "tenants", label: "Tenants" },
        { id: "checkpoints", label: "Checkpoints" },
        { id: "signals", label: "Signals" },
        { id: "associations", label: "Associations" },
        { id: "audit", label: "Audit" },
        { id: "test", label: "Test decisions" },
      ],
    };
  },
  methods: {
    navigate: function (view) {
      this.$root.switchView(view);
      this.$root.mobileNavOpen = false;
    },
  },
};
</script>
