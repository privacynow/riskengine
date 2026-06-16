<template>
  <div class="loading-skeleton" :class="{ 'loading-skeleton--block': block }" />
</template>

<script setup lang="ts">
defineProps<{
  block?: boolean;
}>();
</script>
