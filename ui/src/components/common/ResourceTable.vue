<template>
  <div class="resource-table-wrap">
    <div v-if="!mobile" class="resource-table-desktop">
      <slot name="table" />
    </div>
    <div v-else class="resource-card-list">
      <slot name="cards" />
    </div>
  </div>
</template>

<script>
export default {
  name: "ResourceTable",
  data: function () {
    return { mobile: false };
  },
  mounted: function () {
    var self = this;
    self._mq = window.matchMedia("(max-width: 768px)");
    self.mobile = self._mq.matches;
    self._onChange = function (e) {
      self.mobile = e.matches;
    };
    if (self._mq.addEventListener) {
      self._mq.addEventListener("change", self._onChange);
    } else {
      self._mq.addListener(self._onChange);
    }
  },
  beforeUnmount() {
    if (this._mq && this._onChange) {
      if (this._mq.removeEventListener) {
        this._mq.removeEventListener("change", this._onChange);
      } else {
        this._mq.removeListener(this._onChange);
      }
    }
  },
};
</script>
