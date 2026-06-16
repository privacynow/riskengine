<template>
  <div class="app-shell" :class="{ 'drawer-open': $root.mobileNavOpen }">
    <div class="demo-banner">
      Local demo only — do not expose publicly without real auth.
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
      <TenantContext />
      <NoticeBanner />
      <main class="page-content">
        <OverviewView v-if="$root.view === 'overview'" />
        <TenantsView v-else-if="$root.view === 'tenants'" />
        <CheckpointsView v-else-if="$root.view === 'checkpoints'" />
        <SignalsView v-else-if="$root.view === 'signals'" />
        <AssociationsView v-else-if="$root.view === 'associations'" />
        <AuditSearchView v-else-if="$root.view === 'audit'" />
        <DecisionTestView v-else-if="$root.view === 'test'" />
      </main>
    </div>
    <div
      class="drawer-backdrop"
      :class="{ visible: $root.mobileNavOpen }"
      @click="$root.mobileNavOpen = false"
    ></div>
  </div>
</template>

<script>
import SidebarNav from "@/components/layout/SidebarNav.vue";
import TopBar from "@/components/layout/TopBar.vue";
import TenantContext from "@/components/layout/TenantContext.vue";
import NoticeBanner from "@/components/layout/NoticeBanner.vue";
import OverviewView from "@/components/overview/OverviewView.vue";
import TenantsView from "@/components/tenants/TenantsView.vue";
import CheckpointsView from "@/components/checkpoints/CheckpointsView.vue";
import SignalsView from "@/components/signals/SignalsView.vue";
import AssociationsView from "@/components/associations/AssociationsView.vue";
import AuditSearchView from "@/components/search/AuditSearchView.vue";
import DecisionTestView from "@/components/test/DecisionTestView.vue";

export default {
  name: "AppShell",
  data() {
    return { faviconUrl: import.meta.env.BASE_URL + "assets/favicon.svg" };
  },
  components: {
    SidebarNav,
    TopBar,
    TenantContext,
    NoticeBanner,
    OverviewView,
    TenantsView,
    CheckpointsView,
    SignalsView,
    AssociationsView,
    AuditSearchView,
    DecisionTestView,
  },
};
</script>
