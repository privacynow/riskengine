<template>
  <div class="audit-search-view">
    <PageHeader
      title="Audit explorer"
      subtitle="Search decision history, signal failures, and version promotions."
    />

    <DataToolbar>
      <select v-model="entityType" class="toolbar-select" @change="onEntityTypeChange">
        <option value="decisions">Decisions</option>
        <option value="signal_logs">Signal logs</option>
        <option value="promotions">Promotions</option>
      </select>
      <input
        v-model="query"
        type="search"
        placeholder="Search text"
        class="toolbar-grow"
      />
      <template v-if="entityType !== 'promotions'">
        <input v-model="correlationId" type="search" placeholder="Correlation ID" />
        <input v-model="applicantId" type="search" placeholder="Applicant ID" />
      </template>
      <template v-if="entityType === 'decisions'">
        <input v-model="fromDate" type="date" aria-label="From date" />
        <input v-model="toDate" type="date" aria-label="To date" />
      </template>
      <label v-else-if="entityType === 'signal_logs'" class="checkbox-field toolbar-checkbox">
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

    <WorkbenchLayout v-else :split="detailOpen">
      <template #master>
        <template v-if="entityType === 'decisions'">
          <div v-if="decisions.length" class="card workbench-list-card">
            <div class="list-row-stack">
              <DecisionListRow
                v-for="res in decisions"
                :key="res.id"
                :decision="res"
                :selected="selectedDecisionId === res.id"
                @open="openDecision(res.id)"
              />
            </div>
          </div>
          <EmptyState v-else title="No decisions" message="Run a search to view records." />
        </template>

        <template v-else-if="entityType === 'signal_logs'">
          <div v-if="signalLogs.length" class="card workbench-list-card">
            <div class="list-row-stack">
              <SignalLogListRow
                v-for="res in signalLogs"
                :key="res.id"
                :log="res"
                :selected="selectedSignalLogId === res.id"
                @open="openSignalLog(res.id)"
              />
            </div>
          </div>
          <EmptyState v-else title="No signal logs" message="Search signal execution logs." />
        </template>

        <template v-else>
          <div v-if="promotions.length" class="card workbench-list-card">
            <div class="list-row-stack">
              <PromotionListRow
                v-for="res in promotions"
                :key="res.id"
                :promotion="res"
                :selected="selectedPromotionId === res.id"
                @open="openPromotion(res.id)"
              />
            </div>
          </div>
          <EmptyState v-else title="No promotions" message="Search promotion audit records." />
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
          <h3>Signal triage</h3>
          <button type="button" class="btn-ghost btn-sm" @click="closePanel">Close</button>
        </div>
        <div class="workbench-detail-body">
          <SignalLogDetailPanel :log="selectedSignalLog ?? null" />
        </div>
      </template>

      <template v-else-if="entityType === 'promotions' && selectedPromotionId" #detail>
        <div class="workbench-detail-header">
          <h3>Promotion audit</h3>
          <button type="button" class="btn-ghost btn-sm" @click="closePanel">Close</button>
        </div>
        <div class="workbench-detail-body">
          <LoadingSkeleton v-if="detailLoading" block />
          <PromotionDetailPanel v-else :promotion="selectedPromotion ?? null" />
        </div>
      </template>
    </WorkbenchLayout>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { storeToRefs } from "pinia";
import { routeWithTenant } from "@/app/tenantNav";
import DataToolbar from "@/components/primitives/DataToolbar.vue";
import EmptyState from "@/components/primitives/EmptyState.vue";
import AppPagination from "@/components/primitives/AppPagination.vue";
import PageHeader from "@/components/workbench/PageHeader.vue";
import WorkbenchLayout from "@/components/workbench/WorkbenchLayout.vue";
import LoadingSkeleton from "@/components/workbench/LoadingSkeleton.vue";
import PromotionListRow from "@/components/workbench/PromotionListRow.vue";
import DecisionListRow from "@/components/overview/DecisionListRow.vue";
import SignalLogListRow from "@/components/overview/SignalLogListRow.vue";
import DecisionDetailPanel from "@/components/domain/audit/DecisionDetailPanel.vue";
import SignalLogDetailPanel from "@/components/domain/audit/SignalLogDetailPanel.vue";
import PromotionDetailPanel from "@/components/domain/audit/PromotionDetailPanel.vue";
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
  promotions,
  page,
  totalPages,
  loading,
  selectedDecisionId,
  selectedSignalLogId,
  selectedPromotionId,
  decisionDetail,
  detailLoading,
  selectedSignalLog,
  selectedPromotion,
} = storeToRefs(auditStore);

const { search, selectDecision, selectSignalLog, selectPromotion, closeDetail } = auditStore;

const detailOpen = computed(() => {
  if (entityType.value === "decisions") return !!selectedDecisionId.value;
  if (entityType.value === "signal_logs") return !!selectedSignalLogId.value;
  return !!selectedPromotionId.value;
});

function auditRouteName() {
  if (entityType.value === "signal_logs") return "audit-signal-logs";
  if (entityType.value === "promotions") return "audit-promotions";
  return "audit-decisions";
}

watch(
  () => route.meta.auditType,
  (auditType) => {
    if (auditType === "signal_logs") entityType.value = "signal_logs";
    else if (auditType === "promotions") entityType.value = "promotions";
    else entityType.value = "decisions";
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

watch(
  () => route.query.promotion,
  async (promotionId) => {
    if (typeof promotionId === "string" && promotionId) {
      await selectPromotion(promotionId);
    }
  },
  { immediate: true }
);

function onEntityTypeChange() {
  closeDetail();
  router.push(routeWithTenant({ name: auditRouteName() }));
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

function openPromotion(id: string) {
  router.push(routeWithTenant({ name: "audit-promotions", query: { promotion: id } }));
}

function closePanel() {
  closeDetail();
  router.push(routeWithTenant({ name: auditRouteName() }));
}
</script>
