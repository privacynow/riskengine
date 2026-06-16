<template>
  <div class="associations-view">
    <data-toolbar>
      <select v-model="$root.assocMode" class="toolbar-select">
        <option value="checkpoint">By checkpoint</option>
        <option value="signal">By signal</option>
      </select>
      <input
        v-if="$root.assocMode === 'checkpoint'"
        v-model="$root.assocCheckpointSearchTerm"
        type="search"
        placeholder="Search checkpoints"
        class="toolbar-grow"
      />
      <input
        v-else
        v-model="$root.assocSignalSearchTerm"
        type="search"
        placeholder="Search signals"
        class="toolbar-grow"
      />
      <button
        type="button"
        class="btn-secondary"
        @click="$root.assocMode === 'checkpoint' ? $root.searchAssocCheckpoints(1) : $root.searchAssocSignals(1)"
      >
        Search
      </button>
    </data-toolbar>

    <div v-if="$root.assocMode === 'checkpoint'">
      <resource-table v-if="$root.assocCheckpoints.length">
        <template #table>
        <table class="resource-table">
          <thead><tr><th>Checkpoint</th><th>Signals</th><th></th></tr></thead>
          <tbody>
            <template v-for="cp in $root.assocCheckpoints" :key="cp.id">
              <tr>
                <td>{{ cp.name }}</td>
                <td>{{ ($root.assocCheckpointMap[cp.id] && $root.assocCheckpointMap[cp.id].signals || []).length }}</td>
                <td>
                  <button type="button" class="btn-ghost btn-sm" @click="$root.toggleExpandAssocCheckpoint(cp.id)">
                    {{ $root.expandedAssocCheckpoint[cp.id] ? "Hide" : "Manage" }}
                  </button>
                </td>
              </tr>
              <tr v-if="$root.expandedAssocCheckpoint[cp.id]">
                <td colspan="3">
                  <ul class="simple-list">
                    <li v-for="s in ($root.assocCheckpointMap[cp.id] && $root.assocCheckpointMap[cp.id].signals) || []" :key="s.id">
                      {{ s.name }}
                    </li>
                  </ul>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
        </template>
        <template #cards>
          <div v-for="cp in $root.assocCheckpoints" :key="'card-' + cp.id" class="resource-card card">
            <strong>{{ cp.name }}</strong>
            <button type="button" class="btn-ghost btn-sm" @click="$root.toggleExpandAssocCheckpoint(cp.id)">Manage</button>
          </div>
        
        </template>
      </resource-table>
      <empty-state v-else title="No checkpoints" message="Search or load checkpoints to manage associations." ></empty-state>
      <app-pagination
        :page="$root.assocCheckpointPage"
        :total-pages="$root.assocCheckpointTotalPages"
        @prev="$root.prevAssocCheckpointPage()"
        @next="$root.nextAssocCheckpointPage()"
      ></app-pagination>
    </div>

    <div v-else>
      <resource-table v-if="$root.assocSignals.length">
        <template #table>
        <table class="resource-table">
          <thead><tr><th>Signal</th><th>Checkpoints</th><th></th></tr></thead>
          <tbody>
            <template v-for="s in $root.assocSignals" :key="s.id">
              <tr>
                <td>{{ s.name }}</td>
                <td>{{ ($root.assocSignalMap[s.id] && $root.assocSignalMap[s.id].checkpoints || []).length }}</td>
                <td>
                  <button type="button" class="btn-ghost btn-sm" @click="$root.toggleExpandAssocSignal(s.id)">
                    {{ $root.expandedAssocSignal[s.id] ? "Hide" : "Manage" }}
                  </button>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
        </template>
        <template #cards>
          <div v-for="s in $root.assocSignals" :key="'card-' + s.id" class="resource-card card">
            <strong>{{ s.name }}</strong>
          </div>
        
        </template>
      </resource-table>
      <empty-state v-else title="No signals" message="Search signals to manage associations." ></empty-state>
      <app-pagination
        :page="$root.assocSignalPage"
        :total-pages="$root.assocSignalTotalPages"
        @prev="$root.prevAssocSignalPage()"
        @next="$root.nextAssocSignalPage()"
      ></app-pagination>
    </div>
  </div>
</template>

<script>
import DataToolbar from "@/components/common/DataToolbar.vue";
import ResourceTable from "@/components/common/ResourceTable.vue";
import EmptyState from "@/components/common/EmptyState.vue";
import AppPagination from "@/components/common/Pagination.vue";

export default {
  components: { DataToolbar, ResourceTable, EmptyState, AppPagination },
  name: "AssociationsView",
  mounted: function () {
    this.$root.loadAllAssocCheckpoints(1);
  },
};
</script>
