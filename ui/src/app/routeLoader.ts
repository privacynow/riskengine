import type { RouteLocationNormalizedLoaded } from "vue-router";
import router from "@/app/router";
import { useOverviewStore } from "@/stores/overviewStore";
import { useTenantStore } from "@/stores/tenantStore";
import { useCheckpointStore } from "@/stores/checkpointStore";
import { useSignalStore } from "@/stores/signalStore";
import { useAssociationStore } from "@/stores/associationStore";
import { useAuditStore } from "@/stores/auditStore";
import { useDecisionTestStore } from "@/stores/decisionTestStore";

/** Load view data for a route (call after auth + tenant sync). */
export async function loadRouteData(
  to: RouteLocationNormalizedLoaded = router.currentRoute.value
): Promise<void> {
  const tenantStore = useTenantStore();
  if (!tenantStore.allTenants.length) {
    await tenantStore.fetchAllTenants();
  }
  tenantStore.syncTenantFromRoute(to);

  const name = String(to.name ?? "");

  if (name === "overview") {
    await useOverviewStore().load();
    return;
  }
  if (name === "tenants" || name === "tenant-detail") {
    await tenantStore.fetchPage(1);
    return;
  }
  if (name === "checkpoints" || name === "checkpoint-detail") {
    const store = useCheckpointStore();
    await store.loadAll(1);
    const id = to.params?.checkpointId;
    if (typeof id === "string") await store.selectCheckpoint(id);
    else await store.selectCheckpoint(null);
    return;
  }
  if (name === "signals" || name === "signal-detail") {
    const store = useSignalStore();
    await store.loadAll(1);
    const id = to.params?.signalId;
    if (typeof id === "string") await store.selectSignal(id);
    else await store.selectSignal(null);
    return;
  }
  if (name === "associations") {
    const assoc = useAssociationStore();
    assoc.reset();
    await assoc.loadCheckpoints(1);
    return;
  }
  if (name === "audit-decisions" || name === "audit-signal-logs") {
    const audit = useAuditStore();
    audit.entityType = to.meta.auditType === "signal_logs" ? "signal_logs" : "decisions";
    if (useTenantStore().activeTenantId) {
      await audit.search(1);
      const decisionId = to.query?.decision;
      if (typeof decisionId === "string" && decisionId) {
        await audit.selectDecision(decisionId);
      }
    }
    return;
  }
  if (name === "test-decisions") {
    const store = useDecisionTestStore();
    store.reset();
    await store.loadAll(1);
    await store.applyScenarioFromRoute(to.query);
  }
}
