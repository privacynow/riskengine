<template>
  <AppBadge :variant="variant" :text="text" />
</template>

<script setup lang="ts">
import AppBadge from "@/components/primitives/AppBadge.vue";

defineProps<{
  variant: string;
  text: string;
}>();
</script>
