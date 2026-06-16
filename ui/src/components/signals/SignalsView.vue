<template>
  <div class="signals-view">
    <data-toolbar>
      <select v-model="$root.signalsActiveFilter" class="toolbar-select">
        <option value="active">Active only</option>
        <option value="all">All signals</option>
      </select>
      <input
        type="search"
        v-model="$root.signalSearchTerm"
        placeholder="Search signals"
        class="toolbar-grow"
      />
      <button type="button" class="btn-secondary" @click="$root.searchSignals($root.signalSearchTerm, 1)">
        Search
      </button>
      <button type="button" class="btn-secondary" @click="$root.loadAllSignals(1)">Load all</button>
      <button type="button" class="btn-primary" @click="$root.toggleSignalCreateForm()">
        {{ $root.showSignalCreateForm ? "Close" : "Create signal" }}
      </button>
    </data-toolbar>

    <empty-state
      v-if="!$root.currentGlobalTenant"
      title="Select a tenant"
      message="Use the tenant bar above to scope signals."
    ></empty-state>

    <div v-else>
      <signal-form
        v-if="$root.showSignalCreateForm"
        :form-data="$root.newSignalData"
        :create-new="true"
        @save="$root.createSignal()"
        @cancel="$root.showSignalCreateForm = false"
      ></signal-form>

      <resource-table v-if="$root.signals.length">
        <template #table>
        <table class="resource-table">
          <thead>
            <tr>
              <th>Signal</th>
              <th>Type</th>
              <th>Current</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <template v-for="s in $root.signals" :key="s.id">
              <tr>
                <td>{{ s.name }}</td>
                <td><app-badge :variant="badge(s.type)" :text="label(s.type)" ></app-badge></td>
                <td>
                  <app-badge
                    :variant="s.is_current_version ? 'current' : 'inactive'"
                    :text="s.is_current_version ? 'Current' : 'Inactive'"
                  ></app-badge>
                </td>
                <td>
                  <button type="button" class="btn-ghost btn-sm" @click="$root.toggleExpandSignal(s.id)">
                    {{ $root.expandedSignals[s.id] ? "Hide" : "Details" }}
                  </button>
                  <button
                    v-if="!s.is_current_version"
                    type="button"
                    class="btn-secondary btn-sm"
                    @click="$root.setSignalCurrentVersion(s.id)"
                  >
                    Make current
                  </button>
                </td>
              </tr>
              <tr v-if="$root.expandedSignals[s.id]">
                <td colspan="4">
                  <signal-details :signal="s" ></signal-details>
                  <div class="expandable-panel card">
                    <div class="form-field">
                      <label>Description</label>
                      <textarea v-model="$root.signalEdits[s.id].description" rows="2" />
                    </div>
                    <div class="form-field">
                      <label>Cost</label>
                      <input v-model.number="$root.signalEdits[s.id].cost" type="number" min="0" />
                    </div>
                    <div class="form-field">
                      <label>New bearer token (optional)</label>
                      <input v-model="$root.signalEdits[s.id].bearer_token_input" type="password" />
                    </div>
                    <div class="form-actions">
                      <button type="button" class="btn-primary btn-sm" @click="$root.saveSignal(s.id)">Save</button>
                    </div>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
        </template>
        <template #cards>
          <div v-for="s in $root.signals" :key="'card-' + s.id" class="resource-card card">
            <div class="resource-card-header">
              <strong>{{ s.name }}</strong>
              <app-badge :variant="badge(s.type)" :text="label(s.type)" ></app-badge>
            </div>
            <app-badge
              :variant="s.is_current_version ? 'current' : 'inactive'"
              :text="s.is_current_version ? 'Current' : 'Inactive'"
            ></app-badge>
            <div class="resource-card-actions">
              <button type="button" class="btn-ghost btn-sm" @click="$root.toggleExpandSignal(s.id)">
                {{ $root.expandedSignals[s.id] ? "Hide" : "Details" }}
              </button>
            </div>
            <signal-details v-if="$root.expandedSignals[s.id]" :signal="s" ></signal-details>
          </div>
        
        </template>
      </resource-table>

      <empty-state v-else title="No signals" message="Create a signal for this tenant." ></empty-state>

      <app-pagination
        :page="$root.signalPage"
        :total-pages="$root.signalTotalPages"
        @prev="$root.prevSignalPage()"
        @next="$root.nextSignalPage()"
      ></app-pagination>
    </div>
  </div>
</template>

<script>
import * as formatters from "@/api/formatters.js";
import DataToolbar from "@/components/common/DataToolbar.vue";
import ResourceTable from "@/components/common/ResourceTable.vue";
import EmptyState from "@/components/common/EmptyState.vue";
import AppPagination from "@/components/common/Pagination.vue";
import AppBadge from "@/components/common/Badge.vue";
import SignalDetails from "@/components/signals/SignalDetails.vue";
import SignalForm from "@/components/signals/SignalForm.vue";

export default {
  components: { DataToolbar, ResourceTable, EmptyState, AppPagination, AppBadge, SignalDetails, SignalForm },
  name: "SignalsView",
  mounted: function () {
    if (this.$root.currentGlobalTenant) {
      this.$root.loadAllSignals(1);
    }
  },
  methods: {
    badge: function (type) {
      return formatters.signalTypeBadge(type);
    },
    label: function (type) {
      return formatters.signalTypeLabel(type);
    },
  },
};
</script>
