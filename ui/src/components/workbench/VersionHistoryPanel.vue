<template>
  <FormSection title="Version history" subtitle="All versions for this logical name">
    <LoadingSkeleton v-if="loading" block />
    <EmptyState
      v-else-if="!versions.length"
      title="No versions"
      message="Save a new version to build history."
    />
    <div v-else class="version-history">
      <div class="version-history-list">
        <button
          v-for="version in versions"
          :key="version.id"
          type="button"
          class="version-history-row"
          :class="{ selected: version.id === selectedVersionId }"
          @click="selectVersion(version.id)"
        >
          <StatusBadge
            :variant="version.is_current_version ? 'current' : 'inactive'"
            :text="version.is_current_version ? 'Current' : 'Inactive'"
          />
          <span class="version-history-meta">
            <span class="text-mono">{{ shortId(version.id) }}</span>
            <span v-if="version.updated_at" class="text-muted">{{ formatWhen(version.updated_at) }}</span>
          </span>
        </button>
      </div>

      <div v-if="selectedVersion" class="version-history-detail card">
        <div class="version-history-detail-header">
          <h4>{{ selectedVersion.is_current_version ? "Current version" : "Historical version" }}</h4>
          <div class="version-history-actions">
            <button
              v-if="canPromote(selectedVersion)"
              type="button"
              class="btn-secondary btn-sm"
              @click="$emit('promote', selectedVersion.id)"
            >
              Promote this version
            </button>
            <button
              v-else-if="canReactivate(selectedVersion)"
              type="button"
              class="btn-secondary btn-sm"
              @click="$emit('reactivate', selectedVersion.id)"
            >
              Reactivate
            </button>
            <button
              v-else-if="selectedVersion.is_current_version"
              type="button"
              class="btn-secondary btn-sm"
              @click="$emit('deactivate', selectedVersion.id)"
            >
              Deactivate current
            </button>
            <RouterLink
              v-if="auditLink"
              class="btn-ghost btn-sm"
              :to="auditLink"
            >
              View promotions
            </RouterLink>
          </div>
        </div>

        <dl class="detail-list detail-list--compact">
          <div><dt>Version ID</dt><dd class="text-mono">{{ selectedVersion.id }}</dd></div>
          <div v-if="selectedVersion.updated_at">
            <dt>Updated</dt><dd>{{ formatWhen(selectedVersion.updated_at) }}</dd>
          </div>
        </dl>

        <div v-if="diffField" class="version-diff">
          <h5>Diff vs current</h5>
          <pre class="code-block version-diff-block">
            <span
              v-for="(line, index) in diffLines"
              :key="index"
              :class="`version-diff-line--${line.kind}`"
            >{{ line.text }}
</span>
          </pre>
        </div>

        <pre v-else class="code-block">{{ primaryContent }}</pre>
      </div>
    </div>
  </FormSection>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { RouterLink } from "vue-router";
import { canPromoteVersion, canReactivateVersion } from "@/api/formatters";
import type { Checkpoint, Signal } from "@/api/types";
import { routeWithTenant } from "@/app/tenantNav";
import EmptyState from "@/components/primitives/EmptyState.vue";
import FormSection from "@/components/workbench/FormSection.vue";
import LoadingSkeleton from "@/components/workbench/LoadingSkeleton.vue";
import StatusBadge from "@/components/workbench/StatusBadge.vue";
import { diffLines as buildDiffLines } from "@/utils/textDiff";

type VersionResource = Signal | Checkpoint;

const props = defineProps<{
  resourceType: "signal" | "checkpoint";
  resourceId: string;
  resourceName: string;
  versions: VersionResource[];
  loading?: boolean;
  diffField?: "expression_body" | "dsl_expression";
}>();

defineEmits<{
  promote: [id: string];
  deactivate: [id: string];
  reactivate: [id: string];
}>();

const selectedVersionId = ref<string | null>(null);

watch(
  () => [props.resourceId, props.versions] as const,
  () => {
    selectedVersionId.value = props.resourceId;
  },
  { immediate: true }
);

const selectedVersion = computed(() =>
  props.versions.find((v) => v.id === selectedVersionId.value) ?? null
);

const currentVersion = computed(() => props.versions.find((v) => v.is_current_version) ?? null);

const primaryContent = computed(() => {
  const version = selectedVersion.value;
  if (!version) return "";
  if (props.resourceType === "checkpoint") {
    return (version as Checkpoint).dsl_expression || "";
  }
  return (version as Signal).expression_body || (version as Signal).method_of_call || "";
});

const diffLines = computed(() => {
  if (!props.diffField || !selectedVersion.value || !currentVersion.value) return [];
  const before =
    props.diffField === "dsl_expression"
      ? String((selectedVersion.value as Checkpoint).dsl_expression || "")
      : String((selectedVersion.value as Signal).expression_body || "");
  const after =
    props.diffField === "dsl_expression"
      ? String((currentVersion.value as Checkpoint).dsl_expression || "")
      : String((currentVersion.value as Signal).expression_body || "");
  if (selectedVersion.value.id === currentVersion.value.id) return [];
  return buildDiffLines(before, after);
});

const auditLink = computed(() =>
  routeWithTenant({
    name: "audit-promotions",
    query: { q: props.resourceName },
  })
);

function canPromote(version: VersionResource) {
  return canPromoteVersion(version);
}

function canReactivate(version: VersionResource) {
  return canReactivateVersion(version);
}

function selectVersion(id: string) {
  selectedVersionId.value = id;
}

function shortId(id: string) {
  return id.slice(0, 8);
}

function formatWhen(iso: string) {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}
</script>
