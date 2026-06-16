<template>
  <div class="checkpoint-form card">
    <div class="form-field">
      <label>Name</label>
      <input v-if="createNew" type="text" v-model="formData.name" required />
      <div v-else class="static-field">{{ formData.name }}</div>
    </div>
    <div class="form-field">
      <label>Description</label>
      <textarea v-model="formData.description" rows="2" />
    </div>
    <div class="form-field">
      <label>Type</label>
      <input type="text" v-model="formData.type" />
    </div>
    <div class="form-field">
      <label>DSL expression</label>
      <textarea v-model="formData.dsl_expression" class="code-input" rows="4" />
    </div>
    <div class="form-field checkbox-field">
      <label>
        <input type="checkbox" v-model="formData.makeCurrentVersion" />
        Make current version
      </label>
    </div>

    <checkpoint-signals-panel
      v-if="createNew && showSignals"
      :associated-signals="formData.associatedSignals || []"
      :search-results="formData.signalSearchResults || []"
      :search-query="formData.signalSearch || ''"
      :current-page="formData.signalPage || 1"
      :total-pages="formData.signalTotalPages || 1"
      @add="$emit('add-signal', $event)"
      @remove="$emit('remove-signal', $event)"
      @search="$emit('search-signals', $event)"
      @load-all="$emit('load-all-signals')"
      @page-change="$emit('signal-page-change', $event)"
    ></checkpoint-signals-panel>

    <div class="form-actions">
      <button type="button" class="btn-secondary" @click="$emit('cancel')">Cancel</button>
      <button type="button" class="btn-primary" @click="$emit('save')">Save</button>
    </div>
  </div>
</template>

<script>
import CheckpointSignalsPanel from "@/components/checkpoints/CheckpointSignalsPanel.vue";

export default {
  components: { CheckpointSignalsPanel },
  name: "CheckpointForm",
  props: {
    formData: { type: Object, required: true },
    createNew: { type: Boolean, default: false },
    showSignals: { type: Boolean, default: true },
  },
};
</script>
