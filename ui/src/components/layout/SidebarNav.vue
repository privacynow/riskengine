<template>
  <nav class="sidebar-nav" :class="{ open: mobileNavOpen }">
    <RouterLink
      v-for="item in navItems"
      :key="item.name"
      :to="item.to"
      class="nav-button"
      active-class="active"
      @click="closeMobileNav"
    >
      {{ item.label }}
    </RouterLink>
  </nav>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { storeToRefs } from "pinia";
import { routeWithTenant } from "@/app/tenantNav";
import { useUiStore } from "@/stores/uiStore";

const ui = useUiStore();
const { mobileNavOpen } = storeToRefs(ui);
const { closeMobileNav } = ui;

const navItems = computed(() => [
  { name: "overview", label: "Overview", to: routeWithTenant({ name: "overview" }) },
  { name: "tenants", label: "Tenants", to: routeWithTenant({ name: "tenants" }) },
  { name: "checkpoints", label: "Decision Flows", to: routeWithTenant({ name: "checkpoints" }) },
  { name: "signals", label: "Signal Library", to: routeWithTenant({ name: "signals" }) },
  {
    name: "associations",
    label: "Relationships",
    to: routeWithTenant({ name: "associations" }),
  },
  { name: "audit", label: "Audit", to: routeWithTenant({ name: "audit-decisions" }) },
  {
    name: "test",
    label: "Test Lab",
    to: routeWithTenant({ name: "test-decisions" }),
  },
]);
</script>
