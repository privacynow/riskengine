<template>
  <div class="field-row" :class="{ 'field-row--2': columns === 2 }">
    <slot />
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    columns?: 1 | 2;
  }>(),
  { columns: 1 }
);
</script>
