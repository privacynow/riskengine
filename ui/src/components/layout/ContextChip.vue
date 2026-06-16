<template>
  <div class="context-chip tenant-context-bar">
    <span class="context-chip-icon" aria-hidden="true">
      <Icon name="building" :size="14" />
    </span>
    <label class="context-chip-label" for="tenant-select">Tenant</label>
    <select
      id="tenant-select"
      class="context-chip-select"
      :value="activeTenantId"
      @change="onChange"
    >
      <option value="">Select tenant…</option>
      <option v-for="t in allTenants" :key="t.id" :value="t.id">{{ t.name }}</option>
    </select>
    <Icon name="chevronDown" :size="14" class="context-chip-chevron" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, watch } from "vue";
import { useRoute } from "vue-router";
import { storeToRefs } from "pinia";
import Icon from "@/components/primitives/Icon.vue";
import { useTenantStore } from "@/stores/tenantStore";

const route = useRoute();
const tenantStore = useTenantStore();
const { allTenants, activeTenantId } = storeToRefs(tenantStore);
const { setActiveTenant, fetchAllTenants, syncTenantFromRoute } = tenantStore;

onMounted(() => {
  void fetchAllTenants();
});

watch(
  () => [route.query.tenant, allTenants.value.length] as const,
  () => {
    if (!allTenants.value.length) return;
    syncTenantFromRoute(route);
  },
  { immediate: true }
);

async function onChange(event: Event) {
  const id = (event.target as HTMLSelectElement).value;
  const tenant = allTenants.value.find((t) => t.id === id) || null;
  await setActiveTenant(tenant);
}
</script>
