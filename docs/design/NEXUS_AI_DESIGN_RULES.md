# NEXUS_AI_DESIGN_RULES.md — Rules for Claude/Codex/Hermes doing UI

1. **Load `docs/design/NEXUS_DESIGN.md` first** before editing any frontend file.
2. Never hardcode random spacing/colors — use the spacing scale + theme tokens.
3. Tailwind classes must be complete static strings (JIT can't see `bg-${c}-500`); map variants.
4. Reuse existing components in `src/components/nexus-os/shared` (OSSection, OSCard, Badge, …).
5. Match the surrounding file's idiom, naming, and comment density.
6. Every new surface: define bg + border for BOTH dark and light.
7. Respect mobile dock clearance; test the 2/3 + 1/3 grid collapse.
8. After UI changes: `npm run build`; deploy is approval-gated; bump SW `CACHE_VERSION`.
9. Run `scripts/nexus_code_review_dry_run.py` before committing frontend changes.
10. No fake data in UI; show real empty/loading/error states.
