<template>
  <div
    v-if="uiNotice.visible"
    :class="['notice-banner', uiNotice.isError ? 'notice-error' : 'notice-info']"
  >
    <span>{{ uiNotice.message }}</span>
    <button type="button" class="notice-dismiss" @click="uiNotice.visible = false">×</button>
  </div>
</template>

<script>
import { uiNotice } from "@/stores/notices.js";

export default {
  name: "NoticeBanner",
  data() {
    return { uiNotice };
  },
};
</script>
