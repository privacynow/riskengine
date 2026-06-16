<template>
  <div class="pagination">
    <button type="button" class="btn-secondary btn-sm" :disabled="page <= 1" @click="$emit('prev')">
      Prev
    </button>
    <span>Page {{ page }} of {{ totalPages }}</span>
    <button
      type="button"
      class="btn-secondary btn-sm"
      :disabled="page >= totalPages"
      @click="$emit('next')"
    >
      Next
    </button>
  </div>
</template>

<script>
export default {
  name: "AppPagination",
  props: {
    page: { type: Number, required: true },
    totalPages: { type: Number, required: true },
  },
};
</script>
