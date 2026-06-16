<template>
  <nav class="sidebar-nav" :class="{ open: mobileNavOpen }">
    <div v-for="section in navSections" :key="section.label" class="sidebar-nav-section">
      <span class="sidebar-nav-label">{{ section.label }}</span>
      <NavItem
        v-for="item in section.items"
        :key="item.routeName"
        :to="item.to"
        :label="item.label"
        :icon="item.icon"
        :route-name="item.routeName"
      />
    </div>
  </nav>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { storeToRefs } from "pinia";
import { routeWithTenant } from "@/app/tenantNav";
import NavItem from "@/components/layout/NavItem.vue";
import type { IconName } from "@/icons";
import type { RouteLocationRaw } from "vue-router";
import { useUiStore } from "@/stores/uiStore";

const ui = useUiStore();
const { mobileNavOpen } = storeToRefs(ui);

type NavEntry = {
  routeName: string;
  label: string;
  icon: IconName;
  to: RouteLocationRaw;
};

const navSections = computed(() => {
  const operate: NavEntry[] = [
    {
      routeName: "overview",
      label: "Overview",
      icon: "layoutDashboard",
      to: routeWithTenant({ name: "overview" }),
    },
    {
      routeName: "test-decisions",
      label: "Test Lab",
      icon: "flask",
      to: routeWithTenant({ name: "test-decisions" }),
    },
    {
      routeName: "audit-decisions",
      label: "Audit",
      icon: "scroll",
      to: routeWithTenant({ name: "audit-decisions" }),
    },
  ];

  const design: NavEntry[] = [
    {
      routeName: "checkpoints",
      label: "Decision Flows",
      icon: "gitBranch",
      to: routeWithTenant({ name: "checkpoints" }),
    },
    {
      routeName: "signals",
      label: "Signal Library",
      icon: "radio",
      to: routeWithTenant({ name: "signals" }),
    },
    {
      routeName: "associations",
      label: "Relationships",
      icon: "link",
      to: routeWithTenant({ name: "associations" }),
    },
  ];

  const admin: NavEntry[] = [
    {
      routeName: "tenants",
      label: "Tenants",
      icon: "building",
      to: routeWithTenant({ name: "tenants" }),
    },
  ];

  return [
    { label: "Operate", items: operate },
    { label: "Design", items: design },
    { label: "Admin", items: admin },
  ];
});
</script>
