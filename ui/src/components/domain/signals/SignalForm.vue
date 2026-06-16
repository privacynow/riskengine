<template>
  <div class="signal-form">
    <FormSection title="Identity">
      <FieldRow :columns="2">
        <div class="form-field">
          <label>Name</label>
          <input v-if="createNew" v-model="local.name" type="text" required />
          <div v-else class="static-field">{{ local.name }}</div>
        </div>
        <div class="form-field">
          <label>Type</label>
          <select v-model="local.type" :disabled="!createNew">
            <option value="variable">Variable</option>
            <option value="function">Function</option>
            <option value="expression">Expression</option>
            <option value="internal_endpoint">Internal endpoint</option>
            <option value="external_endpoint">External endpoint</option>
          </select>
        </div>
      </FieldRow>
      <div class="form-field">
        <label>Description</label>
        <textarea v-model="local.description" rows="2" />
      </div>
      <div class="form-field">
        <label>Method of call</label>
        <input v-model="local.method_of_call" type="text" />
      </div>
    </FormSection>

    <FormSection v-if="isFunctionLike" title="Expression">
      <div class="form-field">
        <label>Expression body</label>
        <textarea v-model="local.expression_body" class="code-input" rows="4" />
      </div>
      <div v-if="local.type === 'function'" class="form-field">
        <label>Function params template</label>
        <textarea v-model="local.function_params_template" class="code-input" rows="2" />
      </div>
    </FormSection>

    <FormSection v-if="isEndpoint" title="Endpoint templates">
      <FieldRow :columns="2">
        <div class="form-field">
          <label>HTTP method</label>
          <select v-model="local.http_method">
            <option>GET</option>
            <option>POST</option>
            <option>PUT</option>
            <option>DELETE</option>
          </select>
        </div>
        <SecretInput
          v-model="local.bearer_token"
          label="Bearer token"
          :configured="hasBearerToken"
        />
      </FieldRow>
      <div class="form-field">
        <label>URL params template</label>
        <textarea v-model="local.request_url_params_template" class="code-input" rows="2" />
      </div>
      <div class="form-field">
        <label>Body template</label>
        <textarea v-model="local.request_body_template" class="code-input" rows="3" />
      </div>
      <div class="form-field">
        <label>Headers template</label>
        <textarea v-model="local.request_headers_template" class="code-input" rows="3" />
      </div>
    </FormSection>

    <FormSection title="Runtime policy">
      <FieldRow :columns="2">
        <div class="form-field">
          <label>Cost</label>
          <input v-model.number="local.cost" type="number" min="0" />
        </div>
        <div class="form-field">
          <label>Timeout (seconds)</label>
          <input v-model.number="local.timeout_seconds" type="number" min="1" />
        </div>
      </FieldRow>
      <FieldRow :columns="2">
        <div class="form-field">
          <label>Evaluation order</label>
          <input v-model.number="local.order_of_evaluation" type="number" min="1" />
        </div>
        <div class="form-field">
          <label>Cache expiration (seconds)</label>
          <input v-model.number="local.cache_expiration_seconds" type="number" min="0" />
        </div>
      </FieldRow>
      <FieldRow :columns="2">
        <div class="form-field checkbox-field">
          <label>
            <input v-model="local.can_run_in_parallel" type="checkbox" />
            Can run in parallel
          </label>
        </div>
        <div class="form-field checkbox-field">
          <label>
            <input v-model="local.allow_caching" type="checkbox" />
            Allow caching
          </label>
        </div>
      </FieldRow>
      <div class="form-field checkbox-field">
        <label>
          <input v-model="local.global_reuse" type="checkbox" />
          Global reuse across applicants
        </label>
      </div>
    </FormSection>

    <FormSection v-if="!createNew" title="Versioning & promotion" subtitle="Promotion requires an audited reason">
      <p class="field-hint">
        Saving creates a new signal version. Promote from the signal list with a required reason —
        promotion is enforced server-side and recorded in the audit log.
      </p>
    </FormSection>

    <div class="form-actions">
      <button type="button" class="btn-secondary" @click="onCancel">Cancel</button>
      <button type="button" class="btn-primary" @click="onSave">Save</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { isEndpointSignalType } from "@/api/formatters";
import type { SignalDraft } from "@/api/types";
import FormSection from "@/components/workbench/FormSection.vue";
import FieldRow from "@/components/workbench/FieldRow.vue";
import SecretInput from "@/components/workbench/SecretInput.vue";

const props = defineProps<{
  modelValue: SignalDraft;
  createNew?: boolean;
  hasBearerToken?: boolean;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: SignalDraft];
  save: [value: SignalDraft];
  cancel: [];
}>();

const local = ref<SignalDraft>({ ...props.modelValue });

watch(
  () => props.modelValue,
  (value) => {
    local.value = { ...value };
  },
  { deep: true }
);

const isEndpoint = computed(() => isEndpointSignalType(local.value.type));
const isFunctionLike = computed(
  () => local.value.type === "function" || local.value.type === "expression"
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
