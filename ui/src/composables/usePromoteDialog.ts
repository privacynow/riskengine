import { ref } from "vue";

type PromoteOptions = {
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  reasonLabel?: string;
  reasonPlaceholder?: string;
  requireReason?: boolean;
};

const open = ref(false);
const title = ref("Promote version");
const message = ref("");
const confirmLabel = ref("Promote");
const cancelLabel = ref("Cancel");
const reasonLabel = ref("Promotion reason");
const reasonPlaceholder = ref("Why is this version going live?");
const reason = ref("");
const requireReason = ref(true);

let resolver: ((value: string | null) => void) | null = null;

export function usePromoteDialog() {
  function promote(options: PromoteOptions): Promise<string | null> {
    title.value = options.title;
    message.value = options.message;
    confirmLabel.value = options.confirmLabel ?? "Promote";
    cancelLabel.value = options.cancelLabel ?? "Cancel";
    reasonLabel.value = options.reasonLabel ?? "Promotion reason";
    reasonPlaceholder.value =
      options.reasonPlaceholder ?? "Why is this version going live?";
    requireReason.value = options.requireReason ?? true;
    reason.value = "";
    open.value = true;
    return new Promise<string | null>((resolve) => {
      resolver = resolve;
    });
  }

  function accept() {
    const trimmed = reason.value.trim();
    if (requireReason.value && !trimmed) return;
    open.value = false;
    resolver?.(trimmed || null);
    resolver = null;
  }

  function dismiss() {
    open.value = false;
    resolver?.(null);
    resolver = null;
  }

  return {
    open,
    title,
    message,
    confirmLabel,
    cancelLabel,
    reasonLabel,
    reasonPlaceholder,
    reason,
    requireReason,
    promote,
    accept,
    dismiss,
  };
}
