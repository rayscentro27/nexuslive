# Repo Hygiene Policy

This policy keeps `~/nexus-ai` a clean, reviewable source repository. It exists
because the repo once grew a single branch with ~1,700 files — most of them
runtime state, logs, transcripts, screenshots, and generated content that should
never have been in git.

Enforced by:
- [`AGENTS.md`](../AGENTS.md) — agent operating rules
- [`scripts/check_repo_hygiene.sh`](../scripts/check_repo_hygiene.sh) — staged-file guard
- [`scripts/check_pr_size.sh`](../scripts/check_pr_size.sh) — PR size guard
- [`tests/test_repo_hygiene_policy.sh`](../tests/test_repo_hygiene_policy.sh) — tests for the above

## Directory layout (where things belong)

| Location | Purpose | In git? |
|---|---|---|
| `~/nexus-ai` | **Development repo only** — source code, tests, docs, scripts | ✅ yes |
| `~/nexus-ai-worker` | **Stable runtime checkout only** — do not touch unless asked | ✅ (separate checkout) |
| `~/nexus-runtime` | Logs, locks, receipts, pid files, generated state | ❌ no |
| `~/nexus-research-data` | Transcripts, VTTs, summaries, raw research | ❌ no |
| `~/nexus-artifacts` | Reports, screenshots, generated content, exports | ❌ no |

Runtime/generated output must be written to the runtime/research/artifacts
locations above (or `.gitignore`d in-place), never staged into `~/nexus-ai`.

## Branch & PR rules

- **One branch = one PR = one purpose.** No mixed-concern branches.
- **Archive/source branches are not merge targets.** Branches like
  `feature/vibe-trading-hermes-adapter` are used to *extract* small clean PRs;
  they are never merged directly.
- **PR size target: under 60 changed files.** The hard limit is enforced by
  `check_pr_size.sh`; exceeding it requires Ray's explicit approval and the
  `--override` flag.
- Clean PRs must include a **validation summary** and an **explicit list of the
  staged files**.

## Files that must never be committed

`.env` and `.env.*` (except `.env.example`), `*.lock`, `*.pid`, `logs/`,
`reports/`, `artifacts/`, `research-engine/**/*.vtt`,
`research-engine/**/*.summary`, `docs/content/`, `tool-lab/`, `test-results/`,
`supabase/.temp/`, `node_modules/`, `dist/`, `build/`, `.cache/`, image files
(`*.png`, `*.jpg`, `*.jpeg`, `*.webp`), and runtime state files such as
`.telegram*`, `.hermes*_memory.json`, `.circuit_breaker_state.json`,
`.hermes_cli_handoffs.json`, `.telegram_update_offset`.

**Allowed:** `.env.example` (a template with no real values).

## Before every commit / PR

```bash
# 1. Stage explicit paths only — never `git add .` / `git add -A`
git add path/to/changed_file.py tests/test_changed_file.py

# 2. Verify nothing forbidden is staged
scripts/check_repo_hygiene.sh

# 3. Verify the PR is not a monster branch
scripts/check_pr_size.sh main
```

Both guard scripts are **read-only**: they never delete or modify files, never
access the network, and never print file contents.
