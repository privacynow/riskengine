<template>
  <div class="empty-state" :class="{ 'empty-state--panel': variant === 'panel' }">
    <div v-if="icon" class="empty-state-icon" aria-hidden="true">
      <Icon :name="icon" :size="28" />
    </div>
    <h4 class="empty-state-title">{{ title }}</h4>
    <p class="empty-state-description">{{ message }}</p>
    <slot />
  </div>
</template>

<script setup lang="ts">
import Icon from "@/components/primitives/Icon.vue";
import type { IconName } from "@/icons";

withDefaults(
  defineProps<{
    title: string;
    message?: string;
    icon?: IconName;
    variant?: "inline" | "panel";
  }>(),
  {
    message: "",
    icon: undefined,
    variant: "inline",
  }
);
</script>
