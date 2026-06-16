<template>
  <div class="form-field">
    <label v-if="label" :for="inputId">{{ label }}</label>
    <input
      :id="inputId"
      :value="modelValue"
      type="password"
      autocomplete="off"
      :placeholder="placeholder"
      @input="onInput"
    />
    <p v-if="configured && !modelValue" class="field-hint">{{ configuredHint }}</p>
    <p v-if="hint" class="field-hint">{{ hint }}</p>
  </div>
</template>

<script setup lang="ts">
import { useId } from "vue";

withDefaults(
  defineProps<{
    modelValue: string;
    label?: string;
    placeholder?: string;
    hint?: string;
    configured?: boolean;
    configuredHint?: string;
  }>(),
  {
    label: "",
    placeholder: "Leave blank to keep existing",
    hint: "",
    configuredHint: "Secret configured — leave blank to preserve",
  }
);

const emit = defineEmits<{
  "update:modelValue": [value: string];
}>();

const inputId = useId();

function onInput(event: Event) {
  const target = event.target;
  if (target && "value" in target) {
    emit("update:modelValue", String((target as { value: string }).value));
  }
}
</script>
