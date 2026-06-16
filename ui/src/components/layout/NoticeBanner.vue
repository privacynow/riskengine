<template>
  <div v-if="noticeVisible" class="notice-banner" :class="{ error: noticeIsError }">
    <span>{{ noticeMessage }}</span>
    <button type="button" class="btn-ghost btn-sm" @click="dismissNotice">Dismiss</button>
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from "pinia";
import { useUiStore } from "@/stores/uiStore";

const ui = useUiStore();
const { noticeVisible, noticeMessage, noticeIsError } = storeToRefs(ui);
const { dismissNotice } = ui;
</script>
