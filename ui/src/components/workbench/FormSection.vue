<template>
  <section class="form-section">
    <div v-if="title || subtitle" class="form-section-heading">
      <h4 v-if="title" class="form-section-title">{{ title }}</h4>
      <p v-if="subtitle" class="field-hint form-section-subtitle">{{ subtitle }}</p>
    </div>
    <slot />
  </section>
</template>

<script setup lang="ts">
defineProps<{
  title?: string;
  subtitle?: string;
}>();
</script>
