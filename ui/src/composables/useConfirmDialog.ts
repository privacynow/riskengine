import { ref } from "vue";

type ConfirmOptions = {
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
};

const open = ref(false);
const title = ref("");
const message = ref("");
const confirmLabel = ref("Confirm");
const cancelLabel = ref("Cancel");
let resolver: ((confirmed: boolean) => void) | null = null;

export function useConfirmDialog() {
  function confirm(options: ConfirmOptions): Promise<boolean> {
    title.value = options.title;
    message.value = options.message;
    confirmLabel.value = options.confirmLabel ?? "Confirm";
    cancelLabel.value = options.cancelLabel ?? "Cancel";
    open.value = true;
    return new Promise<boolean>((resolve) => {
      resolver = resolve;
    });
  }

  function accept() {
    open.value = false;
    resolver?.(true);
    resolver = null;
  }

  function dismiss() {
    open.value = false;
    resolver?.(false);
    resolver = null;
  }

  return {
    open,
    title,
    message,
    confirmLabel,
    cancelLabel,
    confirm,
    accept,
    dismiss,
  };
}
