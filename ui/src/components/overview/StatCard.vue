<template>
  <article class="stat-card" :class="[`stat-card--${tone}`]">
    <div class="stat-card-head">
      <span class="stat-label">{{ label }}</span>
      <span v-if="icon" class="stat-card-icon" aria-hidden="true">
        <Icon :name="icon" :size="18" />
      </span>
    </div>
    <strong class="stat-value">{{ value }}</strong>
    <p v-if="hint" class="stat-hint">{{ hint }}</p>
  </article>
</template>

<script setup lang="ts">
import Icon from "@/components/primitives/Icon.vue";
import type { IconName } from "@/icons";

withDefaults(
  defineProps<{
    label: string;
    value: string | number;
    hint?: string;
    icon?: IconName;
    tone?: "default" | "primary" | "teal" | "warning" | "danger" | "success";
  }>(),
  {
    hint: "",
    icon: undefined,
    tone: "default",
  }
);
</script>
