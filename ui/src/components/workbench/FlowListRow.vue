<template>
  <div
    class="list-row entity-table-row"
    :class="{ selected }"
    role="button"
    tabindex="0"
    @click="$emit('open')"
    @keydown.enter="$emit('open')"
    @keydown.space.prevent="$emit('open')"
  >
    <StatusBadge
      :variant="checkpoint.is_current_version ? 'current' : 'inactive'"
      :text="checkpoint.is_current_version ? 'Current' : 'Inactive'"
    />
    <div class="list-row-body">
      <span class="list-row-title">{{ checkpoint.name }}</span>
      <span class="list-row-meta">{{ metaLine }}</span>
    </div>
    <div class="list-row-trailing">
      <div v-if="showPromote" class="list-row-actions" @click.stop>
        <button type="button" class="btn-secondary btn-sm" @click="$emit('promote')">
          Promote
        </button>
      </div>
      <div class="list-row-stats">
        <span class="list-row-cost">Max {{ maxCostLabel }}</span>
        <span v-if="timeoutLabel" class="list-row-time">{{ timeoutLabel }}</span>
      </div>
      <span class="list-row-action" aria-hidden="true">
        <Icon name="arrowRight" :size="14" />
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { Checkpoint } from "@/api/types";
import Icon from "@/components/primitives/Icon.vue";
import StatusBadge from "@/components/workbench/StatusBadge.vue";

const props = defineProps<{
  checkpoint: Checkpoint;
  selected?: boolean;
}>();

defineEmits<{
  open: [];
  promote: [];
}>();

const showPromote = computed(() => !props.checkpoint.is_current_version);

const metaLine = computed(() => {
  const parts = [
    props.checkpoint.type || "flow",
    props.checkpoint.description?.trim() || null,
  ].filter(Boolean);
  return parts.join(" · ");
});

const maxCostLabel = computed(() => (props.checkpoint.max_cost ?? 0).toFixed(2));

const timeoutLabel = computed(() => {
  const seconds = props.checkpoint.timeout_seconds;
  if (seconds == null) return "";
  return `${seconds}s timeout`;
});
</script>
