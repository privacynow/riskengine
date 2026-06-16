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

    <FormSection title="Decision DSL">
      <div class="form-field">
        <label>DSL expression</label>
        <textarea v-model="local.dsl_expression" class="code-input" rows="4" />
      </div>
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

    <FormSection title="Versioning">
      <p v-if="!createNew" class="field-hint">
        Saving updates this checkpoint version. Promote separately to make it live.
      </p>
      <div class="form-field checkbox-field">
        <label>
          <input v-model="local.makeCurrentVersion" type="checkbox" />
          Make current version on save
        </label>
      </div>
    </FormSection>

    <div class="form-actions">
      <button type="button" class="btn-secondary" @click="onCancel">Cancel</button>
      <button type="button" class="btn-primary" @click="onSave">Save</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import type { CheckpointDraft } from "@/api/types";
import CheckpointSignalsPanel from "@/components/domain/checkpoints/CheckpointSignalsPanel.vue";
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
