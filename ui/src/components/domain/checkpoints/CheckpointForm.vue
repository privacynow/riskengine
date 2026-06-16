<template>
  <div class="checkpoint-form">
    <FormSection title="Identity">
      <FieldRow :columns="2">
        <div class="form-field">
          <label>Name</label>
          <input v-if="createNew" v-model="local.name" type="text" required />
          <div v-else class="static-field">{{ local.name }}</div>
        </div>
        <div class="form-field">
          <label>Type</label>
          <input v-model="local.type" type="text" />
        </div>
      </FieldRow>
      <div class="form-field">
        <label>Description</label>
        <textarea v-model="local.description" rows="2" />
      </div>
    </FormSection>

    <FormSection title="Decision DSL" subtitle="Preflight validates syntax against associated signal names">
      <div class="form-field">
        <label>DSL expression</label>
        <textarea v-model="local.dsl_expression" class="code-input" rows="4" />
      </div>
      <DslPreflightPanel
        :expression="local.dsl_expression"
        :signal-names="authoringSignalNames"
      />
      <div class="form-field">
        <label>Method of call</label>
        <input v-model="local.method_of_call" type="text" />
      </div>
    </FormSection>

    <FormSection title="Runtime policy">
      <FieldRow :columns="2">
        <div class="form-field">
          <label>Max cost budget</label>
          <input v-model.number="local.max_cost" type="number" min="0" />
        </div>
        <div class="form-field">
          <label>Timeout (seconds)</label>
          <input v-model.number="local.timeout_seconds" type="number" min="1" />
        </div>
      </FieldRow>
      <div class="form-field checkbox-field">
        <label>
          <input v-model="local.override_cost_flag" type="checkbox" />
          Override cost limit on failure
        </label>
      </div>
    </FormSection>

    <FormSection v-if="showSignals" title="Required signals">
      <CheckpointSignalsPanel
        :associated-signals="local.associatedSignals"
        :search-results="local.signalSearchResults"
        :search-query="local.signalSearch"
        :current-page="local.signalPage"
        :total-pages="local.signalTotalPages"
        @add="$emit('add-signal', $event)"
        @remove="$emit('remove-signal', $event)"
        @search="$emit('search-signals', $event)"
        @load-all="$emit('load-all-signals')"
        @page-change="$emit('signal-page-change', $event)"
      />
    </FormSection>

    <FormSection title="Versioning & promotion" subtitle="Promotion requires an audited reason">
      <div class="rule-authoring-panel">
        <p class="field-hint">
          Saves create or update draft versions only. Promote from the flow list when ready —
          promotion is enforced server-side with a required reason and audit record.
        </p>
        <dl v-if="!createNew" class="detail-list detail-list--compact">
          <div><dt>Checkpoint ID</dt><dd class="text-mono">{{ local.id || "—" }}</dd></div>
          <div><dt>Current expression</dt><dd class="text-mono rule-authoring-diff">{{ local.dsl_expression || "—" }}</dd></div>
        </dl>
        <RouterLink
          v-if="!createNew && local.id"
          class="btn-secondary btn-sm"
          :to="testLabLink"
        >
          Draft test in Test Lab
        </RouterLink>
      </div>
    </FormSection>

    <div class="form-actions">
      <button type="button" class="btn-secondary" @click="onCancel">Cancel</button>
      <button type="button" class="btn-primary" @click="onSave">Save version</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { RouterLink } from "vue-router";
import type { CheckpointDraft } from "@/api/types";
import { routeWithTenant } from "@/app/tenantNav";
import CheckpointSignalsPanel from "@/components/domain/checkpoints/CheckpointSignalsPanel.vue";
import DslPreflightPanel from "@/components/workbench/DslPreflightPanel.vue";
import FormSection from "@/components/workbench/FormSection.vue";
import FieldRow from "@/components/workbench/FieldRow.vue";

const props = withDefaults(
  defineProps<{
    modelValue: CheckpointDraft;
    createNew?: boolean;
    showSignals?: boolean;
  }>(),
  { createNew: false, showSignals: true }
);

const emit = defineEmits<{
  "update:modelValue": [value: CheckpointDraft];
  save: [value: CheckpointDraft];
  cancel: [];
  "add-signal": [signalId: string];
  "remove-signal": [signalId: string];
  "search-signals": [query: string];
  "load-all-signals": [];
  "signal-page-change": [page: number];
}>();

const local = ref<CheckpointDraft>({ ...props.modelValue });

const authoringSignalNames = computed(() =>
  local.value.associatedSignals.map((signal) => signal.name).filter(Boolean)
);

const testLabLink = computed(() =>
  local.value.id
    ? routeWithTenant({ name: "test-decisions", query: { checkpoint: local.value.id } })
    : routeWithTenant({ name: "test-decisions" })
);

watch(
  () => props.modelValue,
  (value) => {
    local.value = {
      ...value,
      associatedSignals: [...value.associatedSignals],
      signalSearchResults: [...value.signalSearchResults],
    };
  },
  { deep: true }
);

function onSave() {
  emit("update:modelValue", { ...local.value });
  emit("save", { ...local.value });
}

function onCancel() {
  local.value = { ...props.modelValue };
  emit("cancel");
}
</script>
