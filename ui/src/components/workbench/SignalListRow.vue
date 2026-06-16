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
    <StatusBadge :variant="typeVariant" :text="typeLabel" />
    <div class="list-row-body">
      <span class="list-row-title">{{ signal.name }}</span>
      <span class="list-row-meta">{{ metaLine }}</span>
    </div>
    <div class="list-row-trailing">
      <div v-if="showPromote" class="list-row-actions" @click.stop>
        <button type="button" class="btn-secondary btn-sm" @click="$emit('promote')">
          Promote
        </button>
      </div>
      <div class="list-row-stats">
        <span class="list-row-cost">Cost {{ costLabel }}</span>
        <span class="list-row-time">{{ versionLabel }}</span>
      </div>
      <span class="list-row-action" aria-hidden="true">
        <Icon name="arrowRight" :size="14" />
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { Signal } from "@/api/types";
import { signalTypeBadge, signalTypeLabel } from "@/api/formatters";
import Icon from "@/components/primitives/Icon.vue";
import StatusBadge from "@/components/workbench/StatusBadge.vue";

const props = defineProps<{
  signal: Signal;
  selected?: boolean;
}>();

defineEmits<{
  open: [];
  promote: [];
}>();

const showPromote = computed(() => !props.signal.is_current_version);

const typeVariant = computed(() => signalTypeBadge(props.signal.type));
const typeLabel = computed(() => signalTypeLabel(props.signal.type));

const metaLine = computed(() => {
  const parts = [
    props.signal.is_current_version ? "Current version" : "Inactive version",
    props.signal.has_bearer_token ? "Bearer secret" : null,
    props.signal.description?.trim() || null,
  ].filter(Boolean);
  return parts.join(" · ");
});

const costLabel = computed(() => (props.signal.cost ?? 0).toFixed(2));
const versionLabel = computed(() =>
  props.signal.is_current_version ? "Active" : "Needs promote"
);
</script>
