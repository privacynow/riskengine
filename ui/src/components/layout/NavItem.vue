<template>
  <RouterLink
    :to="to"
    class="sidebar-nav-item"
    :class="{ active: isActive }"
    @click="onNavigate"
  >
    <span class="nav-icon-tile">
      <Icon :name="icon" :size="16" />
    </span>
    <span class="nav-label">{{ label }}</span>
  </RouterLink>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useRoute, RouterLink } from "vue-router";
import type { RouteLocationRaw } from "vue-router";
import Icon from "@/components/primitives/Icon.vue";
import type { IconName } from "@/icons";
import { useUiStore } from "@/stores/uiStore";

const props = defineProps<{
  to: RouteLocationRaw;
  label: string;
  icon: IconName;
  routeName: string;
}>();

const route = useRoute();
const ui = useUiStore();

const DETAIL_ROUTE_GROUPS: Record<string, string[]> = {
  checkpoints: ["checkpoints", "checkpoint-detail"],
  signals: ["signals", "signal-detail"],
  tenants: ["tenants", "tenant-detail"],
  "audit-decisions": ["audit-decisions", "audit-signal-logs", "audit-promotions"],
};

const isActive = computed(() => {
  const name = String(route.name);
  const group = DETAIL_ROUTE_GROUPS[props.routeName];
  if (group) return group.includes(name);
  return name === props.routeName;
});

function onNavigate() {
  ui.closeMobileNav();
}
</script>
