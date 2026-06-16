<template>
  <component
    :is="iconComponent"
    class="de-icon"
    :size="size"
    :stroke-width="strokeWidth"
    aria-hidden="true"
  />
</template>

<script setup lang="ts">
import { computed } from "vue";
import { icons, type IconName } from "@/icons";

const props = withDefaults(
  defineProps<{
    name: IconName;
    size?: number;
    strokeWidth?: number;
  }>(),
  {
    size: 18,
    strokeWidth: 1.75,
  }
);

const iconComponent = computed(() => icons[props.name]);
</script>

<style scoped>
.de-icon {
  flex-shrink: 0;
  display: block;
}
</style>
