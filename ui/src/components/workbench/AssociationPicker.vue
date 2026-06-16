<template>
  <div class="association-picker">
    <div v-if="linkedItems.length" class="association-chips">
      <span v-for="item in linkedItems" :key="item.id" class="association-chip">
        <StatusBadge
          v-if="item.isCurrent === false"
          variant="inactive"
          text="Inactive"
        />
        <span>{{ item.name }}</span>
        <button
          v-if="removable"
          type="button"
          class="btn-ghost btn-sm"
          aria-label="Remove"
          @click="$emit('remove', item.id)"
        >
          ×
        </button>
      </span>
    </div>
    <p v-else class="text-muted">{{ emptyMessage }}</p>

    <DataToolbar v-if="searchable">
      <input
        :value="searchQuery"
        type="search"
        :placeholder="searchPlaceholder"
        class="toolbar-grow"
        @input="onSearch"
      />
      <button type="button" class="btn-secondary btn-sm" @click="$emit('load-all')">Load all</button>
    </DataToolbar>

    <ResourceTable v-if="candidates.length">
      <template #table>
        <table class="resource-table">
          <thead>
            <tr>
              <th>Name</th>
              <th v-if="showType">Type</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in candidates" :key="item.id">
              <td>{{ item.name }}</td>
              <td v-if="showType">{{ item.type || "—" }}</td>
              <td>
                <button
                  type="button"
                  class="btn-secondary btn-sm"
                  :disabled="isLinked(item.id)"
                  @click="$emit('add', item.id)"
                >
                  {{ isLinked(item.id) ? "Linked" : "Add" }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </template>
      <template #cards>
        <div v-for="item in candidates" :key="'card-' + item.id" class="resource-card card">
          <strong>{{ item.name }}</strong>
          <span v-if="showType" class="text-muted">{{ item.type }}</span>
          <button
            type="button"
            class="btn-secondary btn-sm"
            :disabled="isLinked(item.id)"
            @click="$emit('add', item.id)"
          >
            {{ isLinked(item.id) ? "Linked" : "Add" }}
          </button>
        </div>
      </template>
    </ResourceTable>

    <AppPagination
      v-if="candidates.length && totalPages > 1"
      :page="page"
      :total-pages="totalPages"
      @prev="page > 1 && $emit('page-change', page - 1)"
      @next="page < totalPages && $emit('page-change', page + 1)"
    />
  </div>
</template>

<script setup lang="ts">
import DataToolbar from "@/components/primitives/DataToolbar.vue";
import ResourceTable from "@/components/primitives/ResourceTable.vue";
import AppPagination from "@/components/primitives/AppPagination.vue";
import StatusBadge from "@/components/workbench/StatusBadge.vue";

export type AssociationItem = {
  id: string;
  name: string;
  type?: string;
  isCurrent?: boolean;
};

const props = withDefaults(
  defineProps<{
    linkedItems: AssociationItem[];
    candidates?: AssociationItem[];
    searchQuery?: string;
    page?: number;
    totalPages?: number;
    searchable?: boolean;
    removable?: boolean;
    showType?: boolean;
    emptyMessage?: string;
    searchPlaceholder?: string;
  }>(),
  {
    candidates: () => [],
    searchQuery: "",
    page: 1,
    totalPages: 1,
    searchable: true,
    removable: true,
    showType: true,
    emptyMessage: "Nothing linked yet.",
    searchPlaceholder: "Search to add…",
  }
);

const emit = defineEmits<{
  add: [id: string];
  remove: [id: string];
  search: [query: string];
  "load-all": [];
  "page-change": [page: number];
}>();

function isLinked(id: string) {
  return props.linkedItems.some((item) => item.id === id);
}

function onSearch(event: Event) {
  const target = event.target;
  if (target && "value" in target) {
    emit("search", String((target as { value: string }).value));
  }
}
</script>
