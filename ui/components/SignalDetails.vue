<!-- SignalDetails.vue -->
<template>
  <div class="signal-details">
    <div class="detail-section">
      <h4>Basic Information</h4>
      <table class="detail-table">
        <tr>
          <td class="label">Type:</td>
          <td>{{ signal.type }}</td>
        </tr>
        <tr>
          <td class="label">Method of Call:</td>
          <td>{{ signal.method_of_call || 'N/A' }}</td>
        </tr>
        <tr>
          <td class="label">Cost:</td>
          <td>{{ signal.cost }}</td>
        </tr>
      </table>
    </div>

    <div class="detail-section" v-if="signal.type === 'http'">
      <h4>HTTP Endpoint Details</h4>
      <table class="detail-table">
        <tr>
          <td class="label">HTTP Method:</td>
          <td>{{ signal.http_method }}</td>
        </tr>
        <tr>
          <td class="label">URL Parameters Template:</td>
          <td><pre>{{ signal.request_url_params_template || 'N/A' }}</pre></td>
        </tr>
        <tr>
          <td class="label">Body Template:</td>
          <td><pre>{{ signal.request_body_template || 'N/A' }}</pre></td>
        </tr>
        <tr>
          <td class="label">Headers Template:</td>
          <td><pre>{{ signal.request_headers_template || 'N/A' }}</pre></td>
        </tr>
      </table>
    </div>

    <div class="detail-section" v-if="signal.type === 'function'">
      <h4>Function Details</h4>
      <table class="detail-table">
        <tr>
          <td class="label">Expression Body:</td>
          <td><pre>{{ signal.expression_body || 'N/A' }}</pre></td>
        </tr>
        <tr>
          <td class="label">Function Parameters:</td>
          <td><pre>{{ signal.function_params_template || 'N/A' }}</pre></td>
        </tr>
      </table>
    </div>

    <div class="detail-section">
      <h4>Parameters</h4>
      <table class="detail-table">
        <tr>
          <td class="label">Parameter Placeholders:</td>
          <td>
            <span v-if="signal.param_placeholders && signal.param_placeholders.length">
              <ul class="param-list">
                <li v-for="param in signal.param_placeholders" :key="param">{{ param }}</li>
              </ul>
            </span>
            <span v-else>No parameters required</span>
          </td>
        </tr>
      </table>
    </div>

    <div class="detail-section">
      <h4>Additional Settings</h4>
      <table class="detail-table">
        <tr>
          <td class="label">Cache Expiration:</td>
          <td>{{ signal.cache_expiration_seconds }} seconds</td>
        </tr>
        <tr>
          <td class="label">Timeout:</td>
          <td>{{ signal.timeout_seconds }} seconds</td>
        </tr>
        <tr>
          <td class="label">Can Run in Parallel:</td>
          <td>{{ signal.can_run_in_parallel ? 'Yes' : 'No' }}</td>
        </tr>
        <tr>
          <td class="label">Order of Evaluation:</td>
          <td>{{ signal.order_of_evaluation }}</td>
        </tr>
        <tr>
          <td class="label">Allow Caching:</td>
          <td>{{ signal.allow_caching ? 'Yes' : 'No' }}</td>
        </tr>
        <tr>
          <td class="label">Global Reuse:</td>
          <td>{{ signal.global_reuse ? 'Yes' : 'No' }}</td>
        </tr>
      </table>
    </div>
  </div>
</template>

<script>
export default {
  name: 'SignalDetails',
  props: {
    signal: {
      type: Object,
      required: true
    }
  }
}
</script>

<style scoped>
.signal-details {
  padding: 15px;
  background-color: #f8f9fa;
  border-radius: 4px;
  margin: 10px 0;
}

.detail-section {
  margin-bottom: 20px;
}

.detail-section:last-child {
  margin-bottom: 0;
}

.detail-section h4 {
  color: #2c3e50;
  margin-bottom: 10px;
  font-size: 1.1em;
  border-bottom: 1px solid #dee2e6;
  padding-bottom: 5px;
}

.detail-table {
  width: 100%;
  border-collapse: collapse;
}

.detail-table td {
  padding: 6px 10px;
  vertical-align: top;
}

.detail-table td.label {
  width: 180px;
  color: #666;
  font-weight: 500;
}

.detail-table pre {
  background-color: #fff;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  padding: 8px;
  margin: 0;
  white-space: pre-wrap;
  font-family: monospace;
  font-size: 0.9em;
}

.param-list {
  list-style: none;
  padding: 0;
  margin: 5px 0;
}

.param-list li {
  display: inline-block;
  background: #e3f2fd;
  padding: 4px 8px;
  border-radius: 4px;
  margin: 2px 4px 2px 0;
  font-family: monospace;
}

@media (max-width: 768px) {
  .signal-details {
    padding: 10px;
  }
  .detail-section {
    margin-bottom: 15px;
  }
  .detail-table pre {
    font-size: 0.8em;
  }
  .param-list li {
    display: block;
    margin: 4px 0;
  }
}
</style> 