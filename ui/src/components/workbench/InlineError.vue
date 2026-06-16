<template>
  <p v-if="message" class="inline-error" role="alert">{{ message }}</p>
</template>

<script setup lang="ts">
defineProps<{
  message?: string;
}>();
</script>
