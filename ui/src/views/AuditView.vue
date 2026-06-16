<template>
  <div class="audit-search-view">
    <PageHeader
      title="Audit explorer"
      subtitle="Search decision history and triage signal execution failures."
    />

    <DataToolbar>
      <select v-model="entityType" class="toolbar-select" @change="onEntityTypeChange">
        <option value="decisions">Decisions</option>
        <option value="signal_logs">Signal logs</option>
      </select>
      <input
        v-model="query"
        type="search"
        placeholder="Search text"
        class="toolbar-grow"
      />
      <input v-model="correlationId" type="search" placeholder="Correlation ID" />
      <input v-model="applicantId" type="search" placeholder="Applicant ID" />
      <template v-if="entityType === 'decisions'">
        <input v-model="fromDate" type="date" aria-label="From date" />
        <input v-model="toDate" type="date" aria-label="To date" />
      </template>
      <label v-else class="checkbox-field toolbar-checkbox">
        <input v-model="failuresOnly" type="checkbox" />
        Failures only
      </label>
      <button type="button" class="btn-primary" @click="runSearch(1)">Search</button>
    </DataToolbar>

    <EmptyState
      v-if="!activeTenant"
      title="Select a tenant"
      message="Use the tenant bar above to scope audit records."
    />

    <LoadingSkeleton v-else-if="loading" block />

    <WorkbenchLayout
      v-else
      :split="entityType === 'decisions' ? !!selectedDecisionId : !!selectedSignalLogId"
    >
      <template #master>
        <template v-if="entityType === 'decisions'">
          <ResourceTable v-if="decisions.length">
            <template #table>
              <table class="resource-table">
                <thead>
                  <tr>
                    <th>Result</th>
                    <th>Flow</th>
                    <th>Applicant</th>
                    <th>When</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="res in decisions"
                    :key="res.id"
                    class="entity-table-row"
                    :class="{ selected: selectedDecisionId === res.id }"
                    @click="openDecision(res.id)"
                  >
                    <td>{{ res.final_decision_value }}</td>
                    <td>{{ res.checkpoint_name || "—" }}</td>
                    <td>{{ res.applicant_id || "—" }}</td>
                    <td>{{ formatWhen(res.decision_timestamp) }}</td>
                  </tr>
                </tbody>
              </table>
            </template>
            <template #cards>
              <div
                v-for="res in decisions"
                :key="'card-' + res.id"
                class="resource-card card"
                :class="{ selected: selectedDecisionId === res.id }"
                @click="openDecision(res.id)"
              >
                <strong>{{ res.final_decision_value }}</strong>
                <span class="text-muted">{{ res.checkpoint_name }}</span>
              </div>
            </template>
          </ResourceTable>
          <EmptyState v-else title="No decisions" message="Run a search to view records." />
        </template>

        <template v-else>
          <ResourceTable v-if="signalLogs.length">
            <template #table>
              <table class="resource-table">
                <thead>
                  <tr>
                    <th>Signal</th>
                    <th>Value</th>
                    <th>Status</th>
                    <th>When</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="res in signalLogs"
                    :key="res.id"
                    class="entity-table-row"
                    :class="{ selected: selectedSignalLogId === res.id }"
                    @click="openSignalLog(res.id)"
                  >
                    <td>{{ res.signal_name || res.signal_id }}</td>
                    <td>{{ res.signal_value }}</td>
                    <td>
                      <StatusBadge
                        :variant="res.success === false ? 'inactive' : 'current'"
                        :text="res.success === false ? 'Failed' : 'OK'"
                      />
                    </td>
                    <td>{{ formatWhen(res.started_at) }}</td>
                  </tr>
                </tbody>
              </table>
            </template>
            <template #cards>
              <div
                v-for="res in signalLogs"
                :key="'card-' + res.id"
                class="resource-card card"
                @click="openSignalLog(res.id)"
              >
                <strong>{{ res.signal_name || "signal" }}</strong>
                <StatusBadge
                  :variant="res.success === false ? 'inactive' : 'current'"
                  :text="res.success === false ? 'Failed' : 'OK'"
                />
              </div>
            </template>
          </ResourceTable>
          <EmptyState v-else title="No signal logs" message="Search signal execution logs." />
        </template>

        <AppPagination
          :page="page"
          :total-pages="totalPages"
          @prev="page > 1 && runSearch(page - 1)"
          @next="page < totalPages && runSearch(page + 1)"
        />
      </template>

      <template v-if="entityType === 'decisions' && selectedDecisionId" #detail>
        <div class="workbench-detail-header">
          <h3>Decision detail</h3>
          <button type="button" class="btn-ghost btn-sm" @click="closePanel">Close</button>
        </div>
        <div class="workbench-detail-body">
          <DecisionDetailPanel :detail="decisionDetail" :loading="detailLoading" />
        </div>
      </template>

      <template v-else-if="entityType === 'signal_logs' && selectedSignalLog" #detail>
        <div class="workbench-detail-header">
          <h3>Signal log detail</h3>
          <button type="button" class="btn-ghost btn-sm" @click="closePanel">Close</button>
        </div>
        <div class="workbench-detail-body">
          <SignalLogDetailPanel :log="selectedSignalLog ?? null" />
        </div>
      </template>
    </WorkbenchLayout>
  </div>
</template>

<script setup lang="ts">
import { watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { storeToRefs } from "pinia";
import { routeWithTenant } from "@/app/tenantNav";
import DataToolbar from "@/components/primitives/DataToolbar.vue";
import ResourceTable from "@/components/primitives/ResourceTable.vue";
import EmptyState from "@/components/primitives/EmptyState.vue";
import AppPagination from "@/components/primitives/AppPagination.vue";
import PageHeader from "@/components/workbench/PageHeader.vue";
import WorkbenchLayout from "@/components/workbench/WorkbenchLayout.vue";
import StatusBadge from "@/components/workbench/StatusBadge.vue";
import LoadingSkeleton from "@/components/workbench/LoadingSkeleton.vue";
import DecisionDetailPanel from "@/components/domain/audit/DecisionDetailPanel.vue";
import SignalLogDetailPanel from "@/components/domain/audit/SignalLogDetailPanel.vue";
import { useAuditStore } from "@/stores/auditStore";
import { useTenantStore } from "@/stores/tenantStore";

const route = useRoute();
const router = useRouter();
const auditStore = useAuditStore();
const tenantStore = useTenantStore();

const { activeTenant } = storeToRefs(tenantStore);

const {
  entityType,
  query,
  correlationId,
  applicantId,
  failuresOnly,
  fromDate,
  toDate,
  decisions,
  signalLogs,
  page,
  totalPages,
  loading,
  selectedDecisionId,
  selectedSignalLogId,
  decisionDetail,
  detailLoading,
  selectedSignalLog,
} = storeToRefs(auditStore);

const { search, selectDecision, selectSignalLog, closeDetail } = auditStore;

watch(
  () => route.meta.auditType,
  (auditType) => {
    entityType.value = auditType === "signal_logs" ? "signal_logs" : "decisions";
  },
  { immediate: true }
);

watch(
  () => route.query.decision,
  async (decisionId) => {
    if (typeof decisionId === "string" && decisionId) {
      await selectDecision(decisionId);
    }
  },
  { immediate: true }
);

watch(
  () => route.query.signal_log,
  (signalLogId) => {
    if (typeof signalLogId === "string" && signalLogId) {
      selectSignalLog(signalLogId);
    }
  },
  { immediate: true }
);

function onEntityTypeChange() {
  closeDetail();
  const name = entityType.value === "signal_logs" ? "audit-signal-logs" : "audit-decisions";
  router.push(routeWithTenant({ name }));
}

function runSearch(p: number) {
  closeDetail();
  void search(p);
}

function openDecision(id: string) {
  router.push(routeWithTenant({ name: "audit-decisions", query: { decision: id } }));
}

function openSignalLog(id: string) {
  router.push(routeWithTenant({ name: "audit-signal-logs", query: { signal_log: id } }));
}

function closePanel() {
  closeDetail();
  router.push(routeWithTenant({ name: entityType.value === "signal_logs" ? "audit-signal-logs" : "audit-decisions" }));
}

function formatWhen(value?: string) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}
</script>
