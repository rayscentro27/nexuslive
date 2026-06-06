# Skill: recommend-tool-or-repo

Trigger: Ray shares a repo, tool, or product and asks whether/how to use it.

## Procedure
1. Classify the tool/repo into one bucket:
   - **core now** — directly advances the 30-day monetization goal, low risk, ready to integrate.
   - **later** — useful but not now; store for a future pass.
   - **personal tool** — helps Ray's workflow, not Nexus product surface.
   - **reference only** — study the pattern, don't adopt the code.
   - **ignore** — not a fit.
2. Recommend the integration mode: adapt / fork / wrap / store-for-later / reference-only.
3. Weigh: Nexus OS fit, risk, cost, data privacy, implementation timing.
4. If implementation is actually needed, switch to **Reference Repo Mode**: inspect the real repo before building, don't approximate.

## Output
- The bucket and the one-line reason.
- Recommended mode (adapt/fork/wrap/reference/store).
- Risk + cost + timing note.
- If building: what to inspect first and what's needed from Ray.

## Rules
- Do not install third-party Hermes skills or run repo code without review.
- Prefer existing gateway/local providers; no expensive API-first adoption without approval.
- No credential changes to wire a tool without approval.
