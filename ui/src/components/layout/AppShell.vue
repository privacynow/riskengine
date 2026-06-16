<template>
  <div class="app-shell" :class="{ 'drawer-open': mobileNavOpen }">
    <div v-if="showDevDemoUi" class="demo-banner">
      Development build — bearer-token auth for local use only.
    </div>
    <aside class="sidebar">
      <div class="sidebar-brand">
        <img :src="faviconUrl" alt="" class="brand-icon" />
        <span>Decision Engine</span>
      </div>
      <SidebarNav />
    </aside>
    <div class="app-column">
      <TopBar />
      <TenantSwitcher />
      <NoticeBanner />
      <main class="page-content">
        <slot />
      </main>
    </div>
    <div
      class="drawer-backdrop"
      :class="{ visible: mobileNavOpen }"
      @click="closeMobileNav"
    ></div>
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from "pinia";
import { SHOW_DEV_DEMO_UI } from "@/app/config";
import SidebarNav from "@/components/layout/SidebarNav.vue";
import TopBar from "@/components/layout/TopBar.vue";
import TenantSwitcher from "@/components/layout/TenantSwitcher.vue";
import NoticeBanner from "@/components/layout/NoticeBanner.vue";
import { useUiStore } from "@/stores/uiStore";

const ui = useUiStore();
const { mobileNavOpen } = storeToRefs(ui);
const { closeMobileNav } = ui;
const faviconUrl = import.meta.env.BASE_URL + "assets/favicon.svg";
const showDevDemoUi = SHOW_DEV_DEMO_UI;
</script>
