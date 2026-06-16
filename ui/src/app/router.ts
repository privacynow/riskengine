import { createRouter, createWebHistory } from "vue-router";
import { loadRouteData } from "@/app/routeLoader";
import { useAuthStore } from "@/stores/authStore";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: "/", redirect: { name: "overview" } },
    {
      path: "/overview",
      name: "overview",
      component: () => import("@/views/OverviewView.vue"),
    },
    {
      path: "/tenants",
      name: "tenants",
      component: () => import("@/views/TenantsView.vue"),
    },
    {
      path: "/tenants/:tenantId",
      name: "tenant-detail",
      component: () => import("@/views/TenantsView.vue"),
    },
    {
      path: "/flows",
      redirect: { name: "checkpoints" },
    },
    {
      path: "/checkpoints",
      name: "checkpoints",
      component: () => import("@/views/CheckpointsView.vue"),
    },
    {
      path: "/checkpoints/:checkpointId",
      name: "checkpoint-detail",
      component: () => import("@/views/CheckpointsView.vue"),
    },
    {
      path: "/signals",
      name: "signals",
      component: () => import("@/views/SignalsView.vue"),
    },
    {
      path: "/signals/:signalId",
      name: "signal-detail",
      component: () => import("@/views/SignalsView.vue"),
    },
    {
      path: "/associations",
      name: "associations",
      component: () => import("@/views/AssociationsView.vue"),
    },
    {
      path: "/audit/decisions",
      name: "audit-decisions",
      component: () => import("@/views/AuditView.vue"),
      meta: { auditType: "decisions" },
    },
    {
      path: "/audit/signal-logs",
      name: "audit-signal-logs",
      component: () => import("@/views/AuditView.vue"),
      meta: { auditType: "signal_logs" },
    },
    {
      path: "/audit/promotions",
      name: "audit-promotions",
      component: () => import("@/views/AuditView.vue"),
      meta: { auditType: "promotions" },
    },
    {
      path: "/test-lab",
      redirect: { name: "test-decisions" },
    },
    {
      path: "/test-decisions",
      name: "test-decisions",
      component: () => import("@/views/DecisionTestView.vue"),
    },
    { path: "/:pathMatch(.*)*", redirect: { name: "overview" } },
  ],
});

router.beforeEach(async (to) => {
  const auth = useAuthStore();
  if (!auth.sessionValidated) {
    await auth.initializeFromStorage();
  }
  if (auth.showAuthPrompt) {
    return true;
  }

  await loadRouteData(to);
  return true;
});

export default router;
