<template>
  <AppModal :open="open" :title="title" @close="dismiss">
    <p class="text-muted">{{ message }}</p>
    <div class="form-field">
      <label>{{ reasonLabel }}</label>
      <textarea
        v-model="reason"
        rows="3"
        :placeholder="reasonPlaceholder"
        :aria-required="requireReason"
      />
    </div>
    <template #footer>
      <button type="button" class="btn-secondary" @click="dismiss">{{ cancelLabel }}</button>
      <button
        type="button"
        class="btn-primary"
        :disabled="requireReason && !reason.trim()"
        @click="accept"
      >
        {{ confirmLabel }}
      </button>
    </template>
  </AppModal>
</template>

<script setup lang="ts">
import AppModal from "@/components/primitives/AppModal.vue";
import { usePromoteDialog } from "@/composables/usePromoteDialog";

const {
  open,
  title,
  message,
  confirmLabel,
  cancelLabel,
  reasonLabel,
  reasonPlaceholder,
  reason,
  requireReason,
  accept,
  dismiss,
} = usePromoteDialog();
</script>
