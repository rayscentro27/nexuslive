# NEXUS_DESIGN.md — Load this BEFORE any UI work

Premium, calm, operator-grade UI. Never AI-slop. Use tokens/components, never random values.

## Tokens (use these, don't hardcode)
- Theme via `[data-nexus-theme="dark"|"light"]`; never hardcode hex when a token exists.
- Spacing scale: 4 / 8 / 12 / 16 / 20 / 24 (Tailwind gap-1..gap-6). No arbitrary px.
- Radius: cards `rounded-xl` (12px); pills `rounded-full`. Consistent.
- Text: brand navy `#1A2244` for headings on light; slate-400/500 for meta.
- Accent: indigo/blue (`text-indigo-500`, `#5B7CFA`). One accent per view.

## Layout
- Bento/widget grids: `grid gap-3` / `gap-5`; cards equal padding (`p-3`/`p-4`).
- Dashboard hierarchy: title row → KPI row → action plan → main grid (2/3 + 1/3).
- Mobile: keep ≥ 88px bottom clearance for the dock; never let content sit under it.
- Content cards: readable line length, clear status badge, one primary action.

## Dark/light consistency
- Every surface must have a defined bg + border in both themes.
- Tailwind JIT: only use COMPLETE class strings (no `text-${x}-600`); map variants explicitly.

## Anti-AI-slop checklist
- [ ] No purple-on-purple gradients everywhere; restrained accent
- [ ] Consistent spacing scale (no 13px, 7px one-offs)
- [ ] Real hierarchy (size/weight/color), not all-bold
- [ ] Tokens/components reused, not re-styled per card
- [ ] Empty/loading/error states designed
- [ ] Mobile dock clearance respected
