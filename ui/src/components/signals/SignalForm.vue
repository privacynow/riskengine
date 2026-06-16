<template>
  <div class="signal-form card">
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
      <select v-model="formData.type" :disabled="!createNew">
        <option value="variable">Variable</option>
        <option value="function">Function</option>
        <option value="internal_endpoint">Internal endpoint</option>
        <option value="external_endpoint">External endpoint</option>
      </select>
    </div>
    <div class="form-field">
      <label>Method of call</label>
      <input type="text" v-model="formData.method_of_call" />
    </div>
    <div class="form-field">
      <label>Cost</label>
      <input type="number" v-model.number="formData.cost" min="0" />
    </div>

    <template v-if="isEndpoint">
      <div class="form-field">
        <label>HTTP method</label>
        <select v-model="formData.http_method">
          <option>GET</option>
          <option>POST</option>
          <option>PUT</option>
          <option>DELETE</option>
        </select>
      </div>
      <div class="form-field">
        <label>Outbound bearer token</label>
        <input type="password" v-model="formData.bearer_token" autocomplete="off" placeholder="Leave blank to keep existing" />
      </div>
      <div class="form-field">
        <label>URL params template</label>
        <textarea v-model="formData.request_url_params_template" class="code-input" rows="2" />
      </div>
      <div class="form-field">
        <label>Body template</label>
        <textarea v-model="formData.request_body_template" class="code-input" rows="3" />
      </div>
      <div class="form-field">
        <label>Headers template</label>
        <textarea v-model="formData.request_headers_template" class="code-input" rows="3" />
      </div>
    </template>

    <template v-if="formData.type === 'function'">
      <div class="form-field">
        <label>Expression body</label>
        <textarea v-model="formData.expression_body" class="code-input" rows="3" />
      </div>
      <div class="form-field">
        <label>Function params template</label>
        <textarea v-model="formData.function_params_template" class="code-input" rows="2" />
      </div>
    </template>

    <div class="form-actions">
      <button type="button" class="btn-secondary" @click="$emit('cancel')">Cancel</button>
      <button type="button" class="btn-primary" @click="$emit('save')">Save</button>
    </div>
  </div>
</template>

<script>
import * as formatters from "@/api/formatters.js";

export default {
  name: "SignalForm",
  props: {
    formData: { type: Object, required: true },
    createNew: { type: Boolean, default: false },
  },
  computed: {
    isEndpoint: function () {
      return formatters.isEndpointSignalType(this.formData.type);
    },
  },
};
</script>
