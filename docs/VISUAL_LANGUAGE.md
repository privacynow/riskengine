# Decision Engine — Visual Language

Operational admin console for decision flows, signals, and audit. Warm, trustworthy, and restrained — not playful or consumer-beige.

## Palette

| Role | Token | Use |
|------|-------|-----|
| Canvas | `--color-canvas` | Page background behind panels |
| Surface | `--color-surface-raised` | Cards, sidebar, top bar |
| Ink | `--color-text` | Primary copy |
| Primary | `--color-primary` | Actions, active nav, links |
| Signal | `--color-teal` | Signal library, telemetry |
| Cost / warning | `--color-warning` | Cost pressure, cautions |
| Success / danger | `--color-success`, `--color-danger` | Outcomes, failures |

## Typography

- **UI body:** system sans (`--font-sans`), 14px base
- **Display headings:** page titles in `PageHeader` only; top bar is tenant/session controls
- **Data / IDs:** monospace (`--font-mono`)

## Shape & depth

- **Radius:** 8px for panels and cards (`--radius-lg`); 6px for chips and compact controls
- **Shadows:** light elevation on stat cards and drawer only — no heavy drop shadows
- **Borders:** 1px `--color-border` on raised surfaces

## Layout

- **Sidebar:** grouped nav — OPERATE · DESIGN · ADMIN — icon + label rows, active pill
- **Top bar:** compact tenant **ContextChip** + session controls (no page title)
- **Content:** max-width ~1200px, centered in main column

## Icons

Lucide icons via `@lucide/vue`, 16–18px in nav, 20px in stat cards. Stroke width 1.75.

## Spacing invariants

- **Panel cards** (`.card`): use `PanelCardHeader` / `.card-header` — not `.resource-card-header`
- **Mobile resource cards** (`.resource-card`): use `.resource-card-header` inside padded `.resource-card`
- **Named headers** reset child heading margins: `.card-header`, `.panel-header`, `.workbench-detail-header`, `.page-header-title`
- **Detail bodies**: `.detail-section` + `.detail-list` for definition-list layout
- **Empty states**: `EmptyState` with `.empty-state-title` / `.empty-state-description`; `variant="panel"` for overview panels

## List rows (overview)

- `DecisionListRow` / `SignalLogListRow` use `.list-row` with outcome/status badge, title, meta, stacked stats (cost + time), trailing arrow
- Mobile (≤640px): stats stack vertically; arrow hidden

## Outcome badges

Decision outcomes use `outcome-positive`, `outcome-negative`, `outcome-neutral` — not version badge variants.

## Phase 1 (complete)

Shell tokens, sidebar, tenant chip, overview command center (stat cards, quick actions, list-row activity panels), spacing invariants, Playwright visual snapshots (`visual-review.spec.ts`).

## Phase 2 (in progress)

- **Flows + Signals list rows** — `FlowListRow` / `SignalListRow` on workbench master lists (unified desktop + mobile)
- Test Lab + Audit hero polish
- Audit list rows
- Responsive hardening across workbenches
