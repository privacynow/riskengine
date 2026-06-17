<template>
  <div class="signal-details card">
    <div class="detail-section">
      <h4>Signal details</h4>
      <dl class="detail-list">
        <div>
          <dt>Lifecycle</dt>
          <dd>
            <app-badge
              :variant="signal.is_current_version ? 'current' : 'inactive'"
              :text="signal.is_current_version ? 'Current version' : 'Inactive version'"
            />
          </dd>
        </div>
        <div><dt>Type</dt><dd><app-badge :variant="typeBadge" :text="typeLabel" ></app-badge></dd></div>
        <div><dt>Method</dt><dd>{{ signal.method_of_call || "—" }}</dd></div>
        <div><dt>Cost</dt><dd>{{ signal.cost }}</dd></div>
        <div><dt>Timeout</dt><dd>{{ signal.timeout_seconds }}s</dd></div>
      </dl>
    </div>

    <div v-if="isEndpoint" class="detail-section">
      <h4>Endpoint configuration</h4>
      <dl class="detail-list">
        <div><dt>HTTP method</dt><dd>{{ signal.http_method || "—" }}</dd></div>
        <div><dt>URL params</dt><dd><pre class="code-block">{{ signal.request_url_params_template || "—" }}</pre></dd></div>
        <div><dt>Body</dt><dd><pre class="code-block">{{ signal.request_body_template || "—" }}</pre></dd></div>
        <div><dt>Headers</dt><dd><pre class="code-block">{{ signal.request_headers_template || "—" }}</pre></dd></div>
        <div><dt>Bearer token</dt><dd>{{ signal.has_bearer_token ? "Configured" : "Not set" }}</dd></div>
      </dl>
    </div>

    <div v-if="signal.type === 'function'" class="detail-section">
      <h4>Function</h4>
      <pre class="code-block">{{ signal.expression_body || "—" }}</pre>
      <pre class="code-block">{{ signal.function_params_template || "" }}</pre>
    </div>

    <div v-if="signal.param_placeholders && signal.param_placeholders.length" class="detail-section">
      <h4>Placeholders</h4>
      <div class="chip-row">
        <app-badge
          v-for="p in signal.param_placeholders"
          :key="p"
          variant="variable"
          :text="p"
        ></app-badge>
      </div>
    </div>
  </div>
</template>

<script>
import * as formatters from "@/api/formatters";
import AppBadge from "@/components/primitives/AppBadge.vue";

export default {
  name: "SignalDetails",
  components: { AppBadge },
  props: {
    signal: { type: Object, required: true },
  },
  computed: {
    isEndpoint: function () {
      return formatters.isEndpointSignalType(this.signal.type);
    },
    typeBadge: function () {
      return formatters.signalTypeBadge(this.signal.type);
    },
    typeLabel: function () {
      return formatters.signalTypeLabel(this.signal.type);
    },
  },
};
</script>
