import { reactive } from "vue";

export const uiNotice = reactive({
  message: "",
  isError: false,
  visible: false,
});

let noticeTimer;

export function notify(payload = {}) {
  uiNotice.message = payload.message || "";
  uiNotice.isError = !!payload.isError;
  uiNotice.visible = true;
  if (noticeTimer) {
    clearTimeout(noticeTimer);
  }
  noticeTimer = setTimeout(() => {
    uiNotice.visible = false;
  }, 6000);
}
