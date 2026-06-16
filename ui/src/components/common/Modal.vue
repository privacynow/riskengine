<template>
  <div v-if="open" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content card">
      <h3>{{ title }}</h3>
      <div class="modal-body">
        <slot />
      </div>
      <div class="form-actions">
        <slot name="footer" />
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "AppModal",
  props: {
    open: { type: Boolean, default: false },
    title: { type: String, default: "" },
  },
};
</script>
