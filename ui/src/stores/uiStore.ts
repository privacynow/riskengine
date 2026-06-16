import { defineStore } from "pinia";

let noticeTimer: ReturnType<typeof setTimeout> | undefined;

export const useUiStore = defineStore("ui", {
  state: () => ({
    mobileNavOpen: false,
    noticeMessage: "",
    noticeIsError: false,
    noticeVisible: false,
    globalLoading: false,
  }),
  actions: {
    toggleMobileNav() {
      this.mobileNavOpen = !this.mobileNavOpen;
    },
    closeMobileNav() {
      this.mobileNavOpen = false;
    },
    notify(message: string, isError = false) {
      this.noticeMessage = message;
      this.noticeIsError = isError;
      this.noticeVisible = true;
      if (noticeTimer) clearTimeout(noticeTimer);
      noticeTimer = setTimeout(() => {
        this.noticeVisible = false;
      }, 6000);
    },
    dismissNotice() {
      this.noticeVisible = false;
    },
    setGlobalLoading(loading: boolean) {
      this.globalLoading = loading;
    },
  },
});
