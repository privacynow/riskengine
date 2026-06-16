<template>
  <span :class="['badge', 'badge-' + variant]">{{ text }}</span>
</template>

<script>
export default {
  name: "AppBadge",
  props: {
    variant: { type: String, default: "inactive" },
    text: { type: String, required: true },
  },
};
</script>
