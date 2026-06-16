<template>
  <div class="app-root">
    <AuthModal v-if="showAuthPrompt" />
    <AppShell v-if="isVueReady" />
  </div>
</template>

<script>
import api from "./api/client.js";
import { getStoredAdminToken, setStoredAdminToken } from "./api/auth.js";
import { uiNotice } from "./stores/notices.js";
import coreMixin from "./mixins/core.js";
import overviewMixin from "./mixins/overview.js";
import tenantsMixin from "./mixins/tenants.js";
import checkpointsMixin from "./mixins/checkpoints.js";
import signalsMixin from "./mixins/signals.js";
import associationsMixin from "./mixins/associations.js";
import searchMixin from "./mixins/search.js";
import testMixin from "./mixins/test.js";
import AuthModal from "./components/layout/AuthModal.vue";
import AppShell from "./components/layout/AppShell.vue";

export default {
  name: "AdminApp",
  components: { AuthModal, AppShell },
  mixins: [
    coreMixin,
    overviewMixin,
    tenantsMixin,
    checkpointsMixin,
    signalsMixin,
    associationsMixin,
    searchMixin,
    testMixin,
  ],
  provide() {
    return { admin: this, uiNotice };
  },
  data() {
    return {
      mobileNavOpen: false,
    };
  },
  mounted() {
    if (getStoredAdminToken()) {
      api
        .request("/ui/tenants?page=1&size=1")
        .then((response) => {
          if (!response.ok) {
            throw new Error("Stored admin token rejected.");
          }
          this.bootstrapApp();
        })
        .catch(() => {
          setStoredAdminToken("");
          this.showAuthPrompt = true;
        });
    } else {
      this.showAuthPrompt = true;
    }
  },
};
</script>

<style>
[v-cloak] {
  display: none !important;
}
</style>
