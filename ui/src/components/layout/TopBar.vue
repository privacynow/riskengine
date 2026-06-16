<template>
  <header class="top-bar">
    <div class="top-bar-start">
      <button
        type="button"
        class="top-bar-menu-toggle"
        aria-label="Open navigation"
        @click="toggleMobileNav"
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
      <button type="button" class="btn-secondary btn-sm" @click="logout">Sign out</button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import { storeToRefs } from "pinia";
import { useAuthStore } from "@/stores/authStore";
import { useTenantStore } from "@/stores/tenantStore";
import { useUiStore } from "@/stores/uiStore";

const route = useRoute();
const auth = useAuthStore();
const tenantStore = useTenantStore();
const ui = useUiStore();
const { activeTenant } = storeToRefs(tenantStore);
const { toggleMobileNav } = ui;

const titleMap: Record<string, string> = {
  overview: "Operations overview",
  tenants: "Tenants",
  "tenant-detail": "Tenants",
  checkpoints: "Decision Flows",
  "checkpoint-detail": "Decision Flows",
  signals: "Signal Library",
  "signal-detail": "Signal Library",
  associations: "Relationships",
  "audit-decisions": "Audit explorer",
  "audit-signal-logs": "Audit explorer",
  "test-decisions": "Test Lab",
};

const title = computed(() => titleMap[String(route.name)] || "Decision Engine");
const subtitle = computed(() =>
  activeTenant.value
    ? `Tenant: ${activeTenant.value.name}`
    : "Select a tenant to scope checkpoint and signal work"
);

function logout() {
  auth.logout();
}
</script>
