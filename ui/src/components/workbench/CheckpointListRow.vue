<template>
  <div class="list-row entity-table-row list-row--workbench" :class="{ selected }">
    <StatusBadge
      :variant="checkpoint.is_current_version ? 'current' : 'inactive'"
      :text="checkpoint.is_current_version ? 'Current' : 'Inactive'"
    />
    <button type="button" class="list-row-open" @click="$emit('open')">
      <span class="list-row-body">
        <span class="list-row-title">{{ checkpoint.name }}</span>
        <span class="list-row-meta">{{ metaLine }}</span>
      </span>
      <span class="list-row-trailing">
        <span class="list-row-stats">
          <span class="list-row-cost">{{ capLabel }}</span>
          <span v-if="timeoutLabel" class="list-row-time">{{ timeoutLabel }}</span>
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
import type { Checkpoint } from "@/api/types";
import {
  canPromoteVersion,
  canReactivateVersion,
  formatCheckpointCostCap,
  formatEvalTimeout,
} from "@/api/formatters";
import Icon from "@/components/primitives/Icon.vue";
import StatusBadge from "@/components/workbench/StatusBadge.vue";

const props = withDefaults(
  defineProps<{
    checkpoint: Checkpoint;
    selected?: boolean;
    promotable?: boolean;
  }>(),
  { promotable: true }
);

defineEmits<{
  open: [];
  promote: [];
  deactivate: [];
  reactivate: [];
}>();

const showPromote = computed(
  () => props.promotable && canPromoteVersion(props.checkpoint)
);
const showReactivate = computed(
  () => props.promotable && canReactivateVersion(props.checkpoint)
);
const showDeactivate = computed(
  () => props.promotable && !!props.checkpoint.is_current_version
);
const showLifecycleActions = computed(
  () => showPromote.value || showReactivate.value || showDeactivate.value
);

const metaLine = computed(() => {
  const parts = [
    props.checkpoint.type || "Checkpoint",
    props.checkpoint.override_cost_flag ? "Cost override allowed" : null,
    props.checkpoint.description?.trim() || null,
    !props.checkpoint.is_current_version ? "Older version" : null,
  ].filter(Boolean);
  return parts.join(" · ");
});

const capLabel = computed(() => formatCheckpointCostCap(props.checkpoint.max_cost));

const timeoutLabel = computed(() => formatEvalTimeout(props.checkpoint.timeout_seconds));
</script>
