<template>
  <div class="quick-action-bar" role="toolbar" aria-label="Quick actions">
    <RouterLink
      v-for="action in actions"
      :key="action.label"
      :to="action.to"
      class="quick-action"
    >
      <span class="quick-action-icon" aria-hidden="true">
        <Icon :name="action.icon" :size="16" />
      </span>
      <span class="quick-action-text">
        <span class="quick-action-label">{{ action.label }}</span>
        <span v-if="action.hint" class="quick-action-hint">{{ action.hint }}</span>
      </span>
      <Icon name="arrowRight" :size="14" class="quick-action-arrow" />
    </RouterLink>
  </div>
</template>

<script setup lang="ts">
import { RouterLink, type RouteLocationRaw } from "vue-router";
import Icon from "@/components/primitives/Icon.vue";
import type { IconName } from "@/icons";

defineProps<{
  actions: {
    label: string;
    hint?: string;
    icon: IconName;
    to: RouteLocationRaw;
  }[];
}>();
</script>
