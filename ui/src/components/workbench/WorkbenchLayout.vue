<template>
  <div class="workbench" :class="{ 'workbench--split': split }">
    <aside class="workbench-master">
      <slot name="master" />
    </aside>
    <section v-if="split" class="workbench-detail">
      <slot name="detail" />
    </section>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  split?: boolean;
}>();
</script>
