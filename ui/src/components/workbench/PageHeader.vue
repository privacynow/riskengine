<template>
  <div class="page-header workbench-page-header">
    <Breadcrumbs v-if="breadcrumbs?.length" :items="breadcrumbs" />
    <div class="page-header-row">
      <div>
        <h3 v-if="title" class="page-header-title">{{ title }}</h3>
        <p v-if="subtitle" class="page-header-subtitle">{{ subtitle }}</p>
      </div>
      <div v-if="$slots.actions" class="page-header-actions">
        <slot name="actions" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import Breadcrumbs from "@/components/workbench/Breadcrumbs.vue";

defineProps<{
  title?: string;
  subtitle?: string;
  breadcrumbs?: { label: string; to?: string }[];
}>();
</script>
