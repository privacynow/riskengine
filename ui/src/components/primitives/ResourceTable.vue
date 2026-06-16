<template>
  <div class="resource-table-wrap">
    <div v-if="!mobile || !hasCards" class="resource-table-desktop">
      <slot name="table" />
    </div>
    <div v-else class="resource-card-list">
      <slot name="cards" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, useSlots } from "vue";

const slots = useSlots();
const hasCards = computed(() => Boolean(slots.cards));

const mobile = ref(false);
let mq: MediaQueryList | null = null;
let onChange: ((e: MediaQueryListEvent) => void) | null = null;

onMounted(() => {
  mq = window.matchMedia("(max-width: 768px)");
  mobile.value = mq.matches;
  onChange = (e) => {
    mobile.value = e.matches;
  };
  mq.addEventListener("change", onChange);
});

onBeforeUnmount(() => {
  if (mq && onChange) mq.removeEventListener("change", onChange);
});
</script>
