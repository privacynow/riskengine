<template>
  <div class="app-root">
    <AuthModal v-if="showAuthPrompt" />
    <AppShell v-if="isReady">
      <RouterView />
    </AppShell>
    <ConfirmDialog />
    <PromoteDialog />
  </div>
</template>

<script setup lang="ts">
import { RouterView } from "vue-router";
import { storeToRefs } from "pinia";
import { useAuthStore } from "@/stores/authStore";
import AuthModal from "@/components/layout/AuthModal.vue";
import AppShell from "@/components/layout/AppShell.vue";
import ConfirmDialog from "@/components/layout/ConfirmDialog.vue";
import PromoteDialog from "@/components/workbench/PromoteDialog.vue";

const auth = useAuthStore();
const { isReady, showAuthPrompt } = storeToRefs(auth);
</script>

<style>
[v-cloak] {
  display: none !important;
}
</style>
