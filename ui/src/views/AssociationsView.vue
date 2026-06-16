<template>
  <div class="associations-view">
    <DataToolbar>
      <select v-model="mode" class="toolbar-select">
        <option value="checkpoint">By checkpoint</option>
        <option value="signal">By signal</option>
      </select>
      <input
        v-if="mode === 'checkpoint'"
        v-model="checkpointSearchTerm"
        type="search"
        placeholder="Search checkpoints"
        class="toolbar-grow"
      />
      <input
        v-else
        v-model="signalSearchTerm"
        type="search"
        placeholder="Search signals"
        class="toolbar-grow"
      />
      <button
        type="button"
        class="btn-secondary"
        @click="mode === 'checkpoint' ? searchCheckpoints(1) : searchSignals(1)"
      >
        Search
      </button>
    </DataToolbar>

    <div v-if="mode === 'checkpoint'">
      <ResourceTable v-if="checkpoints.length">
        <template #table>
          <table class="resource-table">
            <thead>
              <tr>
                <th>Checkpoint</th>
                <th>Signals</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <template v-for="cp in checkpoints" :key="cp.id">
                <tr>
                  <td>{{ cp.name }}</td>
                  <td>{{ (checkpointMap[cp.id]?.signals || []).length }}</td>
                  <td>
                    <button
                      type="button"
                      class="btn-ghost btn-sm"
                      @click="toggleExpandCheckpoint(cp.id)"
                    >
                      {{ expandedCheckpoint[cp.id] ? "Hide" : "Manage" }}
                    </button>
                  </td>
                </tr>
                <tr v-if="expandedCheckpoint[cp.id]">
                  <td colspan="3">
                    <ul class="simple-list">
                      <li
                        v-for="s in checkpointMap[cp.id]?.signals || []"
                        :key="s.id"
                      >
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
          <div
            v-for="cp in checkpoints"
            :key="'card-' + cp.id"
            class="resource-card card"
          >
            <strong>{{ cp.name }}</strong>
            <button
              type="button"
              class="btn-ghost btn-sm"
              @click="toggleExpandCheckpoint(cp.id)"
            >
              {{ expandedCheckpoint[cp.id] ? "Hide" : "Manage" }}
            </button>
            <ul
              v-if="expandedCheckpoint[cp.id] && (checkpointMap[cp.id]?.signals || []).length"
              class="simple-list"
            >
              <li
                v-for="s in checkpointMap[cp.id]?.signals || []"
                :key="s.id"
              >
                {{ s.name }}
              </li>
            </ul>
            <p v-else-if="expandedCheckpoint[cp.id]" class="text-muted">
              No linked signals.
            </p>
          </div>
        </template>
      </ResourceTable>
      <EmptyState
        v-else
        title="No checkpoints"
        message="Search or load checkpoints to manage associations."
      />
      <AppPagination
        :page="checkpointPage"
        :total-pages="checkpointTotalPages"
        @prev="goToCheckpointPage(checkpointPage - 1)"
        @next="goToCheckpointPage(checkpointPage + 1)"
      />
    </div>

    <div v-else>
      <ResourceTable v-if="signals.length">
        <template #table>
          <table class="resource-table">
            <thead>
              <tr>
                <th>Signal</th>
                <th>Checkpoints</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <template v-for="s in signals" :key="s.id">
                <tr>
                  <td>{{ s.name }}</td>
                  <td>{{ (signalMap[s.id]?.checkpoints || []).length }}</td>
                  <td>
                    <button
                      type="button"
                      class="btn-ghost btn-sm"
                      @click="toggleExpandSignal(s.id)"
                    >
                      {{ expandedSignal[s.id] ? "Hide" : "Manage" }}
                    </button>
                  </td>
                </tr>
                <tr v-if="expandedSignal[s.id]">
                  <td colspan="3">
                    <ul v-if="(signalMap[s.id]?.checkpoints || []).length" class="simple-list">
                      <li v-for="cp in signalMap[s.id]?.checkpoints || []" :key="cp.id">
                        {{ cp.name }}
                      </li>
                    </ul>
                    <p v-else class="text-muted">Not linked to any decision flows.</p>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </template>
        <template #cards>
          <div v-for="s in signals" :key="'card-' + s.id" class="resource-card card">
            <strong>{{ s.name }}</strong>
            <button type="button" class="btn-ghost btn-sm" @click="toggleExpandSignal(s.id)">
              {{ expandedSignal[s.id] ? "Hide" : "Manage" }}
            </button>
            <ul v-if="expandedSignal[s.id] && (signalMap[s.id]?.checkpoints || []).length" class="simple-list">
              <li v-for="cp in signalMap[s.id]?.checkpoints || []" :key="cp.id">
                {{ cp.name }}
              </li>
            </ul>
            <p v-else-if="expandedSignal[s.id]" class="text-muted">
              Not linked to any decision flows.
            </p>
          </div>
        </template>
      </ResourceTable>
      <EmptyState v-else title="No signals" message="Search signals to manage associations." />
      <AppPagination
        :page="signalPage"
        :total-pages="signalTotalPages"
        @prev="goToSignalPage(signalPage - 1)"
        @next="goToSignalPage(signalPage + 1)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from "pinia";
import DataToolbar from "@/components/primitives/DataToolbar.vue";
import ResourceTable from "@/components/primitives/ResourceTable.vue";
import EmptyState from "@/components/primitives/EmptyState.vue";
import AppPagination from "@/components/primitives/AppPagination.vue";
import { useAssociationStore } from "@/stores/associationStore";

const store = useAssociationStore();

const {
  mode,
  checkpointSearchTerm,
  signalSearchTerm,
  checkpoints,
  signals,
  checkpointPage,
  signalPage,
  checkpointTotalPages,
  signalTotalPages,
  expandedCheckpoint,
  expandedSignal,
  checkpointMap,
  signalMap,
} = storeToRefs(store);

const {
  loadCheckpoints,
  searchCheckpoints,
  loadSignals,
  searchSignals,
  toggleExpandCheckpoint,
  toggleExpandSignal,
} = store;

function goToCheckpointPage(p: number) {
  if (checkpointSearchTerm.value.trim()) {
    searchCheckpoints(p);
  } else {
    loadCheckpoints(p);
  }
}

function goToSignalPage(p: number) {
  if (signalSearchTerm.value.trim()) {
    searchSignals(p);
  } else {
    loadSignals(p);
  }
}
</script>
