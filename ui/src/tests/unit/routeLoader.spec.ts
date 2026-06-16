import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import type { RouteLocationNormalizedLoaded } from "vue-router";

const loadOverview = vi.fn();
const loadCheckpoints = vi.fn();
const selectCheckpoint = vi.fn().mockResolvedValue(undefined);
const loadSignals = vi.fn();
const selectSignal = vi.fn().mockResolvedValue(undefined);
const resetAssociation = vi.fn();
const loadAssociationCheckpoints = vi.fn();
const resetDecisionTest = vi.fn();
const loadDecisionTest = vi.fn();
const applyScenarioFromRoute = vi.fn().mockResolvedValue(undefined);
const auditSearch = vi.fn();
const auditSelectDecision = vi.fn().mockResolvedValue(undefined);
const syncTenantFromRoute = vi.fn();
const fetchAllTenants = vi.fn();

vi.mock("@/stores/overviewStore", () => ({
  useOverviewStore: () => ({ load: loadOverview }),
}));
vi.mock("@/stores/checkpointStore", () => ({
  useCheckpointStore: () => ({ loadAll: loadCheckpoints, selectCheckpoint }),
}));
vi.mock("@/stores/signalStore", () => ({
  useSignalStore: () => ({ loadAll: loadSignals, selectSignal }),
}));
vi.mock("@/stores/associationStore", () => ({
  useAssociationStore: () => ({
    reset: resetAssociation,
    loadCheckpoints: loadAssociationCheckpoints,
  }),
}));
vi.mock("@/stores/decisionTestStore", () => ({
  useDecisionTestStore: () => ({
    reset: resetDecisionTest,
    loadAll: loadDecisionTest,
    applyScenarioFromRoute,
  }),
}));
vi.mock("@/stores/auditStore", () => ({
  useAuditStore: () => ({
    entityType: "decisions",
    search: auditSearch,
    selectDecision: auditSelectDecision,
  }),
}));
vi.mock("@/stores/tenantStore", () => ({
  useTenantStore: () => ({
    allTenants: [{ id: "t1", name: "T1" }],
    activeTenant: { id: "t1", name: "T1" },
    activeTenantId: "t1",
    syncTenantFromRoute,
    fetchAllTenants,
    fetchPage: vi.fn(),
  }),
}));
vi.mock("@/app/router", () => ({
  default: { currentRoute: { value: { name: "overview", query: {} } } },
}));

import { loadRouteData } from "@/app/routeLoader";

function routeNamed(
  name: string,
  params: Record<string, string> = {},
  query: Record<string, string> = {}
): RouteLocationNormalizedLoaded {
  return { name, params, query, meta: {} } as RouteLocationNormalizedLoaded;
}

describe("routeLoader", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("loads overview data for overview route", async () => {
    await loadRouteData(routeNamed("overview"));
    expect(loadOverview).toHaveBeenCalledOnce();
    expect(syncTenantFromRoute).toHaveBeenCalledOnce();
  });

  it("loads checkpoints for checkpoint routes", async () => {
    await loadRouteData(routeNamed("checkpoints"));
    expect(loadCheckpoints).toHaveBeenCalledWith(1);
    expect(selectCheckpoint).toHaveBeenCalledWith(null);
  });

  it("loads signals for signal routes", async () => {
    await loadRouteData(routeNamed("signals"));
    expect(loadSignals).toHaveBeenCalledWith(1);
    expect(selectSignal).toHaveBeenCalledWith(null);
  });

  it("selects checkpoint by id on checkpoint-detail route", async () => {
    await loadRouteData(routeNamed("checkpoint-detail", { checkpointId: "cp-1" }));
    expect(loadCheckpoints).toHaveBeenCalledWith(1);
    expect(selectCheckpoint).toHaveBeenCalledWith("cp-1");
  });

  it("selects signal by id on signal-detail route", async () => {
    await loadRouteData(routeNamed("signal-detail", { signalId: "sig-1" }));
    expect(loadSignals).toHaveBeenCalledWith(1);
    expect(selectSignal).toHaveBeenCalledWith("sig-1");
  });

  it("does not load tenant-scoped data for tenants admin route", async () => {
    await loadRouteData(routeNamed("tenants"));
    expect(loadSignals).not.toHaveBeenCalled();
    expect(loadCheckpoints).not.toHaveBeenCalled();
  });

  it("searches audit and selects decision from query", async () => {
    await loadRouteData(
      routeNamed("audit-decisions", {}, { decision: "dec-1" })
    );
    expect(auditSearch).toHaveBeenCalledWith(1);
    expect(auditSelectDecision).toHaveBeenCalledWith("dec-1");
  });

  it("awaits scenario prefill on test-decisions route", async () => {
    let resolveScenario: () => void = () => {};
    const scenarioGate = new Promise<void>((resolve) => {
      resolveScenario = resolve;
    });
    applyScenarioFromRoute.mockImplementation(async () => scenarioGate);

    const loadPromise = loadRouteData(
      routeNamed(
        "test-decisions",
        {},
        {
          checkpoint: "cp-1",
          applicant: "app-1",
          from_decision: "dec-1",
        }
      )
    );

    await expect(
      Promise.race([
        loadPromise.then(() => "done"),
        new Promise((resolve) => setTimeout(() => resolve("pending"), 20)),
      ])
    ).resolves.toBe("pending");

    resolveScenario();
    await loadPromise;

    expect(resetDecisionTest).toHaveBeenCalledOnce();
    expect(loadDecisionTest).toHaveBeenCalledWith(1);
    expect(applyScenarioFromRoute).toHaveBeenCalledWith({
      checkpoint: "cp-1",
      applicant: "app-1",
      from_decision: "dec-1",
    });
  });
});
