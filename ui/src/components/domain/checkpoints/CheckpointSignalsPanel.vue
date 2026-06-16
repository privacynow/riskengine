<template>
  <div class="checkpoint-signals-panel">
    <h4>Associated signals</h4>

    <ul v-if="associatedSignals.length" class="chip-row">
      <li v-for="signal in associatedSignals" :key="signal.id" class="chip">
        <span>{{ signal.name }}</span>
        <button type="button" class="chip-remove" @click="$emit('remove', signal.id)">×</button>
      </li>
    </ul>
    <p v-else class="text-muted">No signals linked yet.</p>

    <div class="signals-picker">
      <data-toolbar>
        <input
          type="search"
          :value="searchQuery"
          placeholder="Search signals to add"
          class="toolbar-grow"
          @input="onSearchInput"
        />
        <button type="button" class="btn-secondary btn-sm" @click="$emit('load-all')">Load all</button>
      </data-toolbar>

      <resource-table v-if="searchResults.length">
        <template #table>
        <table class="resource-table">
          <thead>
            <tr>
              <th>Signal</th>
              <th>Type</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="signal in searchResults" :key="signal.id">
              <td>{{ signal.name }}</td>
              <td>{{ signal.type }}</td>
              <td>
                <button
                  type="button"
                  class="btn-secondary btn-sm"
                  :disabled="isLinked(signal.id)"
                  @click="$emit('add', signal.id)"
                >
                  {{ isLinked(signal.id) ? "Added" : "Add" }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        </template>
        <template #cards>
          <div v-for="signal in searchResults" :key="'card-' + signal.id" class="resource-card card">
            <strong>{{ signal.name }}</strong>
            <span class="text-muted">{{ signal.type }}</span>
            <button
              type="button"
              class="btn-secondary btn-sm"
              :disabled="isLinked(signal.id)"
              @click="$emit('add', signal.id)"
            >
              {{ isLinked(signal.id) ? "Added" : "Add" }}
            </button>
          </div>
        
        </template>
      </resource-table>
      <empty-state v-else title="No signals" message="Search or load signals to associate." ></empty-state>

      <app-pagination
        v-if="searchResults.length"
        :page="currentPage"
        :total-pages="totalPages"
        @prev="currentPage > 1 && $emit('page-change', currentPage - 1)"
        @next="currentPage < totalPages && $emit('page-change', currentPage + 1)"
      ></app-pagination>
    </div>
  </div>
</template>

<script>
import DataToolbar from "@/components/primitives/DataToolbar.vue";
import ResourceTable from "@/components/primitives/ResourceTable.vue";
import EmptyState from "@/components/primitives/EmptyState.vue";
import AppPagination from "@/components/primitives/AppPagination.vue";

export default {
  name: "CheckpointSignalsPanel",
  components: { DataToolbar, ResourceTable, EmptyState, AppPagination },
  props: {
    associatedSignals: { type: Array, default: function () { return []; } },
    searchResults: { type: Array, default: function () { return []; } },
    searchQuery: { type: String, default: "" },
    currentPage: { type: Number, default: 1 },
    totalPages: { type: Number, default: 1 },
  },
  methods: {
    isLinked: function (signalId) {
      return this.associatedSignals.some(function (s) { return s.id === signalId; });
    },
    onSearchInput: function (event) {
      this.$emit("search", event.target.value);
    },
  },
};
</script>
