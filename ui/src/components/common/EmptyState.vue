<template>
  <div class="empty-state">
    <h4>{{ title }}</h4>
    <p>{{ message }}</p>
    <slot />
  </div>
</template>

<script>
export default {
  name: "EmptyState",
  props: {
    title: { type: String, default: "Nothing here" },
    message: { type: String, default: "" },
  },
};
</script>
