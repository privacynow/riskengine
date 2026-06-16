import { describe, expect, it } from "vitest";
import { parseApiErrorBody } from "@/api/errors";
import { totalPages, emptySignalDraft } from "@/api/types";
import { signalTypeLabel, decisionOutcomeVariant } from "@/api/formatters";

describe("api/errors", () => {
  it("parses FastAPI detail string", () => {
    expect(parseApiErrorBody('{"detail":"Forbidden"}')).toBe("Forbidden");
  });
});

describe("api/types", () => {
  it("computes total pages", () => {
    expect(totalPages(11, 5)).toBe(3);
  });

  it("creates empty signal draft", () => {
    const draft = emptySignalDraft();
    expect(draft.type).toBe("variable");
    expect(draft.bearer_token).toBe("");
  });
});

describe("api/formatters", () => {
  it("labels signal types", () => {
    expect(signalTypeLabel("internal_endpoint")).toBe("Internal endpoint");
  });

  it("maps decision outcomes to outcome badge variants", () => {
    expect(decisionOutcomeVariant("True")).toBe("outcome-positive");
    expect(decisionOutcomeVariant("denied")).toBe("outcome-negative");
    expect(decisionOutcomeVariant("manual_review")).toBe("outcome-neutral");
  });
});
