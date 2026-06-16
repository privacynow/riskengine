<template>
  <div class="checkpoints-view">
    <data-toolbar>
      <select v-model="$root.checkpointsActiveFilter" class="toolbar-select">
        <option value="active">Active only</option>
        <option value="all">All checkpoints</option>
      </select>
      <input
        type="search"
        v-model="$root.checkpointSearchTerm"
        placeholder="Search checkpoints"
        class="toolbar-grow"
      />
      <button type="button" class="btn-secondary" @click="$root.searchCheckpoints(1)">Search</button>
      <button type="button" class="btn-secondary" @click="$root.loadAllCheckpoints(1)">Load all</button>
      <button type="button" class="btn-primary" @click="$root.toggleCheckpointCreateForm()">
        {{ $root.showCheckpointCreateForm ? "Close" : "Create checkpoint" }}
      </button>
    </data-toolbar>

    <empty-state
      v-if="!$root.currentGlobalTenant"
      title="Select a tenant"
      message="Use the tenant bar above to scope checkpoints."
    ></empty-state>

    <div v-else>
      <checkpoint-form
        v-if="$root.showCheckpointCreateForm"
        :form-data="$root.newCheckpointData"
        :create-new="true"
        @save="$root.createCheckpoint()"
        @cancel="$root.showCheckpointCreateForm = false"
        @add-signal="$root.addSignalToCheckpoint($event)"
        @remove-signal="$root.removeSignalFromCheckpoint($event)"
        @search-signals="onCreateSignalSearch"
        @load-all-signals="$root.loadAllSignalsForCheckpoint(1)"
        @signal-page-change="$root.onCheckpointSignalPageChange($event)"
      ></checkpoint-form>

      <resource-table v-if="$root.checkpoints.length">
        <template #table>
        <table class="resource-table">
          <thead>
            <tr>
              <th>Checkpoint</th>
              <th>Type</th>
              <th>Current</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <template v-for="cp in $root.checkpoints" :key="cp.id">
              <tr>
                <td>{{ cp.name }}</td>
                <td>{{ cp.type }}</td>
                <td>
                  <app-badge
                    :variant="cp.is_current_version ? 'current' : 'inactive'"
                    :text="cp.is_current_version ? 'Current' : 'Inactive'"
                  ></app-badge>
                </td>
                <td>
                  <button type="button" class="btn-ghost btn-sm" @click="$root.toggleExpandCheckpoint(cp.id)">
                    {{ $root.expandedCheckpoints[cp.id] ? "Hide" : "Edit" }}
                  </button>
                  <button
                    v-if="!cp.is_current_version"
                    type="button"
                    class="btn-secondary btn-sm"
                    @click="$root.setCheckpointCurrentVersion(cp.id)"
                  >
                    Make current
                  </button>
                </td>
              </tr>
              <tr v-if="$root.expandedCheckpoints[cp.id]">
                <td colspan="4">
                  <checkpoint-form
                    :form-data="$root.checkpointEdits[cp.id]"
                    :show-signals="false"
                    @save="$root.saveCheckpoint(cp.id)"
                    @cancel="$root.expandedCheckpoints[cp.id] = false"
                  ></checkpoint-form>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
        </template>
        <template #cards>
          <div v-for="cp in $root.checkpoints" :key="'card-' + cp.id" class="resource-card card">
            <div class="resource-card-header">
              <strong>{{ cp.name }}</strong>
              <span class="text-muted">{{ cp.type }}</span>
            </div>
            <app-badge
              :variant="cp.is_current_version ? 'current' : 'inactive'"
              :text="cp.is_current_version ? 'Current' : 'Inactive'"
            ></app-badge>
            <div class="resource-card-actions">
              <button type="button" class="btn-ghost btn-sm" @click="$root.toggleExpandCheckpoint(cp.id)">
                {{ $root.expandedCheckpoints[cp.id] ? "Hide" : "Edit" }}
              </button>
            </div>
            <checkpoint-form
              v-if="$root.expandedCheckpoints[cp.id]"
              :form-data="$root.checkpointEdits[cp.id]"
              @save="$root.saveCheckpoint(cp.id)"
              @cancel="$root.expandedCheckpoints[cp.id] = false"
            ></checkpoint-form>
          </div>
        
        </template>
      </resource-table>

      <empty-state v-else title="No checkpoints" message="Create a checkpoint for this tenant." ></empty-state>

      <app-pagination
        :page="$root.checkpointPage"
        :total-pages="$root.checkpointTotalPages"
        @prev="$root.prevCheckpointPage()"
        @next="$root.nextCheckpointPage()"
      ></app-pagination>
    </div>

    <app-modal
      :open="$root.showCheckpointConfirmation"
      title="Checkpoint already exists"
      @close="$root.cancelCheckpointCreation()"
    >
      <p>
        A checkpoint named <strong>{{ $root.newCheckpointData.name }}</strong> already exists.
        Creating a new row will add a version.
      </p>
      <template #footer>
        <button type="button" class="btn-secondary" @click="$root.cancelCheckpointCreation()">Cancel</button>
        <button type="button" class="btn-primary" @click="$root.confirmCheckpointCreation()">Create version</button>
      </template>
    </app-modal>
  </div>
</template>

<script>
import DataToolbar from "@/components/common/DataToolbar.vue";
import ResourceTable from "@/components/common/ResourceTable.vue";
import EmptyState from "@/components/common/EmptyState.vue";
import AppPagination from "@/components/common/Pagination.vue";
import AppBadge from "@/components/common/Badge.vue";
import CheckpointForm from "@/components/checkpoints/CheckpointForm.vue";
import AppModal from "@/components/common/Modal.vue";

export default {
  components: { DataToolbar, ResourceTable, EmptyState, AppPagination, AppBadge, CheckpointForm, AppModal },
  name: "CheckpointsView",
  mounted: function () {
    if (this.$root.currentGlobalTenant) {
      this.$root.loadAllCheckpoints(1);
    }
  },
  methods: {
    onCreateSignalSearch: function (query) {
      this.$root.newCheckpointData.signalSearch = query;
      this.$root.fetchCheckpointSignalSearch(1);
    },
  },
};
</script>
