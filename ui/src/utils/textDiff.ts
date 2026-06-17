/**
 * Simple line-level diff for version history panels.
 */
export type DiffLine = {
  text: string;
  kind: "same" | "removed" | "added";
};

export function diffLines(before: string, after: string): DiffLine[] {
  const left = (before || "").split("\n");
  const right = (after || "").split("\n");
  const max = Math.max(left.length, right.length);
  const lines: DiffLine[] = [];
  for (let i = 0; i < max; i += 1) {
    const a = left[i] ?? "";
    const b = right[i] ?? "";
    if (a === b) {
      if (a) lines.push({ text: a, kind: "same" });
    } else {
      if (a) lines.push({ text: a, kind: "removed" });
      if (b) lines.push({ text: b, kind: "added" });
    }
  }
  return lines;
}
