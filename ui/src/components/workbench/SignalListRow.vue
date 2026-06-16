<template>
  <div class="list-row entity-table-row list-row--workbench" :class="{ selected }">
    <StatusBadge :variant="typeVariant" :text="typeLabel" />
    <button type="button" class="list-row-open" @click="$emit('open')">
      <span class="list-row-body">
        <span class="list-row-title">{{ signal.name }}</span>
        <span class="list-row-meta">{{ metaLine }}</span>
      </span>
      <span class="list-row-trailing">
        <span class="list-row-stats">
          <span class="list-row-cost">{{ costLabel }}</span>
          <span class="list-row-time">{{ versionLabel }}</span>
        </span>
        <span class="list-row-action" aria-hidden="true">
          <Icon name="arrowRight" :size="14" />
        </span>
      </span>
    </button>
    <div v-if="showLifecycleActions" class="list-row-actions">
      <button
        v-if="showPromote"
        type="button"
        class="btn-secondary btn-sm list-row-promote"
        @click="$emit('promote')"
      >
        Promote
      </button>
      <button
        v-else-if="showReactivate"
        type="button"
        class="btn-secondary btn-sm list-row-promote"
        @click="$emit('reactivate')"
      >
        Reactivate
      </button>
      <button
        v-else-if="showDeactivate"
        type="button"
        class="btn-secondary btn-sm list-row-promote"
        @click="$emit('deactivate')"
      >
        Deactivate
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { Signal } from "@/api/types";
import {
  canPromoteVersion,
  canReactivateVersion,
  formatSignalRuntimeCost,
  signalTypeBadge,
  signalTypeLabel,
} from "@/api/formatters";
import Icon from "@/components/primitives/Icon.vue";
import StatusBadge from "@/components/workbench/StatusBadge.vue";

const props = defineProps<{
  signal: Signal;
  selected?: boolean;
}>();

defineEmits<{
  open: [];
  promote: [];
  deactivate: [];
  reactivate: [];
}>();

const showPromote = computed(() => canPromoteVersion(props.signal));
const showReactivate = computed(() => canReactivateVersion(props.signal));
const showDeactivate = computed(() => !!props.signal.is_current_version);
const showLifecycleActions = computed(
  () => showPromote.value || showReactivate.value || showDeactivate.value
);

const typeVariant = computed(() => signalTypeBadge(props.signal.type));
const typeLabel = computed(() => signalTypeLabel(props.signal.type));

const metaLine = computed(() => {
  const parts = [
    props.signal.is_current_version ? "Current version" : "Older version",
    props.signal.has_bearer_token ? "Bearer secret" : null,
    props.signal.can_run_in_parallel === false ? "Serial only" : null,
    props.signal.description?.trim() || null,
  ].filter(Boolean);
  return parts.join(" · ");
});

const costLabel = computed(() => formatSignalRuntimeCost(props.signal.cost));

const versionLabel = computed(() =>
  props.signal.is_current_version ? "Active" : "Needs promote"
);
</script>
