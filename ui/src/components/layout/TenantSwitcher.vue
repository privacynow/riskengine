<template>
  <div class="tenant-context-bar">
    <label for="tenant-select">Active tenant</label>
    <select id="tenant-select" :value="activeTenantId" @change="onChange">
      <option value="">— Select tenant —</option>
      <option v-for="t in allTenants" :key="t.id" :value="t.id">{{ t.name }}</option>
    </select>
  </div>
</template>

<script setup lang="ts">
import { onMounted, watch } from "vue";
import { useRoute } from "vue-router";
import { storeToRefs } from "pinia";
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
