<template>
  <FormSection title="Variable values">
    <p class="field-hint">
      Upsert name/value pairs for this variable signal. Values apply to the current signal version.
    </p>
    <FieldRow :columns="2">
      <div class="form-field">
        <label>Name</label>
        <input v-model="draftName" type="text" placeholder="e.g. threshold" />
      </div>
      <div class="form-field">
        <label>Value</label>
        <input v-model="draftValue" type="text" />
      </div>
    </FieldRow>
    <div class="form-actions">
      <button type="button" class="btn-primary btn-sm" :disabled="!draftName" @click="save">
        Save value
      </button>
    </div>
    <InlineError :message="error" />
    <ul v-if="saved.length" class="association-chips">
      <li v-for="row in saved" :key="row.name" class="association-chip">
        <span>{{ row.name }} = {{ row.value || "—" }}</span>
      </li>
    </ul>
  </FormSection>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { variableValuesApi } from "@/api/variableValuesApi";
import { useAuthStore } from "@/stores/authStore";
import { useUiStore } from "@/stores/uiStore";
import FormSection from "@/components/workbench/FormSection.vue";
import FieldRow from "@/components/workbench/FieldRow.vue";
import InlineError from "@/components/workbench/InlineError.vue";

const props = defineProps<{
  signalId: string;
}>();

const draftName = ref("");
const draftValue = ref("");
const error = ref("");
const saved = ref<{ name: string; value: string }[]>([]);

async function save() {
  error.value = "";
  try {
    await variableValuesApi.upsert({
      signal_id: props.signalId,
      name: draftName.value.trim(),
      value: draftValue.value,
    });
    const name = draftName.value.trim();
    const existing = saved.value.find((r) => r.name === name);
    if (existing) existing.value = draftValue.value;
    else saved.value.push({ name, value: draftValue.value });
    draftName.value = "";
    draftValue.value = "";
    useUiStore().notify("Variable value saved.");
  } catch (err) {
    useAuthStore().handleApiError(err);
    error.value = err instanceof Error ? err.message : "Save failed";
  }
}
</script>
