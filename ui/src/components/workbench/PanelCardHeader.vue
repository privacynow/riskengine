<template>
  <div class="card-header panel-card-header">
    <component :is="headingTag" class="panel-card-header-title">{{ title }}</component>
    <div v-if="$slots.actions" class="panel-card-header-actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    title: string;
    headingTag?: "h2" | "h3" | "h4";
  }>(),
  {
    headingTag: "h4",
  }
);
</script>
