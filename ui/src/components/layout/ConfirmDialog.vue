<template>
  <AppModal :open="open" :title="title" @close="dismiss">
    <p class="text-muted">{{ message }}</p>
    <template #footer>
      <button type="button" class="btn-secondary" @click="dismiss">{{ cancelLabel }}</button>
      <button type="button" class="btn-primary" @click="accept">{{ confirmLabel }}</button>
    </template>
  </AppModal>
</template>

<script setup lang="ts">
import AppModal from "@/components/primitives/AppModal.vue";
import { useConfirmDialog } from "@/composables/useConfirmDialog";

const { open, title, message, confirmLabel, cancelLabel, accept, dismiss } =
  useConfirmDialog();
</script>
