<template>
  <section class="form-section">
    <h4 v-if="title" class="form-section-title">{{ title }}</h4>
    <slot />
  </section>
</template>

<script setup lang="ts">
defineProps<{
  title?: string;
}>();
</script>
