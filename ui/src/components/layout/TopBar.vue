<template>
  <header class="top-bar">
    <div class="top-bar-start">
      <button
        type="button"
        class="top-bar-menu-toggle"
        aria-label="Open navigation"
        @click="toggleMobileNav"
      >
        <Icon name="menu" :size="18" />
      </button>
    </div>
    <div class="top-bar-end">
      <ContextChip />
      <button type="button" class="btn-secondary btn-sm" @click="logout">Sign out</button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { useAuthStore } from "@/stores/authStore";
import { useUiStore } from "@/stores/uiStore";
import ContextChip from "@/components/layout/ContextChip.vue";
import Icon from "@/components/primitives/Icon.vue";

const auth = useAuthStore();
const ui = useUiStore();
const { toggleMobileNav } = ui;

function logout() {
  auth.logout();
}
</script>
