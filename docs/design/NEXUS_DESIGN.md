# NEXUS OS — Design Contract

The visual language for Nexus OS. Goal: a premium, compact, controlled operating
system — Apple-style widgets + executive command center. Not a stretched admin table.

## Brand / Layout Direction
- Calm, dense, controlled. Information-rich but never noisy.
- Lavender/blue accent (`#5B7CFA`), dark ink (`#1A2244`), slate neutrals, white cards.
- Cards are widgets, not panels. Mix small / medium / large intentionally.
- Hierarchy first: what matters → what needs attention → status → what's next.

## Spacing Scale (8px rhythm)
| Token | px | Use |
|---|---|---|
| micro | 4 | icon gaps, chip internals |
| tight | 8 | inside compact rows |
| compact | 12 | card internal groups |
| normal | 16 | default gap between elements |
| card-gap | 24 | gap between cards in a grid |
| section | 32 | between dashboard sections |
| major | 48 | between major page regions |
| hero | 64 | page top breathing room (desktop) |

Rules: external spacing > internal spacing. Card padding 20–24px. Sections 24–32px apart.
No random margins — use the wrappers (`NexusPage`, `NexusSection`, `WidgetGrid`).

## Width Rules (critical)
- Page max-width: **1280px**, centered (`mx-auto`). Never edge-to-edge on desktop.
- Readable text blocks: max 720px.
- Metric cards: 220–300px. Compact widgets: 240–340px.
- Action cards: 280–420px. Recommendation cards: 360–640px.
- Tables / detail editors / chat may be full container width; **individual widgets must not**.

## Grid Rules
- Mobile: 1 column. Tablet: 2. Desktop: 3–4 where it reads well.
- Use `WidgetGrid` (auto-fit, minmax) so cards keep natural widths instead of stretching.
- Don't force equal heights unless it helps scanning.
- Wide cards only for high-priority Command Center panels.

## Card Variants
`WidgetCard` / `MetricCard` / `ActionCard` / `RecommendationCard` with tones:
`standard | compact | wide | hero | metric | action | warning | success | muted`.

## Mobile Rules
- One column. No horizontal scroll except the section nav strip.
- Comfortable top padding below nav (not cramped, not oversized).
- Modals: `w-full` with sane `max-w-*`, vertical scroll.
- Tap targets ≥ 36px. Buttons grouped, not spread edge-to-edge.

## Page Structure
1. `PageHeader` — title + one-line subtitle + primary action (right).
2. Status / "needs attention" row (compact).
3. Metric row (`WidgetGrid` of `MetricCard`).
4. Content sections (`NexusSection`), 24–32px apart.
5. Detail / list at the bottom or in a drawer.

## Anti-Patterns (do not do)
- ❌ Giant full-width cards (except tables/editors/detail/chat).
- ❌ Random gradient spam.
- ❌ Every box the same size.
- ❌ Cramped page tops.
- ❌ Weak/identical section headers.
- ❌ Raw admin-dashboard look.
- ❌ Over-padded mobile screens.
- ❌ Fake metrics or guarantees.
- ❌ Visual changes that break function (CRUD, chat, approvals).

## Acceptance Checklist
- [ ] Page content centered at ≤1280px on desktop.
- [ ] No widget stretches full-width unless it's a table/editor/chat.
- [ ] Consistent 24px card gap, 24–32px section gap.
- [ ] Clear hierarchy: attention items visually distinct from status.
- [ ] Metric cards compact, not giant boxes.
- [ ] Mobile: single column, no unintended horizontal scroll.
- [ ] Safety/locked status visible but not alarmist.
- [ ] No business logic, CRUD, chat, or approval flow changed.
