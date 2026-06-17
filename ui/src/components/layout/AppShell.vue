<template>
  <div class="app-shell" :class="{ 'drawer-open': mobileNavOpen }">
    <div v-if="showDevDemoUi" class="demo-banner">
      Development build — bearer-token auth for local use only.
    </div>
    <aside class="sidebar">
      <div class="sidebar-brand">
        <div class="sidebar-product-mark">
          <img :src="faviconUrl" alt="" class="brand-icon" />
        </div>
        <h1 class="brand-title">Decision Engine</h1>
      </div>
      <SidebarNav />
      <footer class="sidebar-footer">
        <p class="sidebar-footer-text">
          Operations console
          <span class="sidebar-footer-sub">Multi-tenant checkpoints</span>
        </p>
      </footer>
    </aside>
    <div class="app-column">
      <TopBar />
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
import NoticeBanner from "@/components/layout/NoticeBanner.vue";
import { useUiStore } from "@/stores/uiStore";

const ui = useUiStore();
const { mobileNavOpen } = storeToRefs(ui);
const { closeMobileNav } = ui;
const faviconUrl = import.meta.env.BASE_URL + "assets/favicon.svg";
const showDevDemoUi = SHOW_DEV_DEMO_UI;
</script>
