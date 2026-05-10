# NotebookLM CLI Install Report (Dry-Run Safe)

Date: 2026-05-10

## Option Audit
- `notebooklm-cli`: available on PyPI (`0.1.12` latest), community/unofficial.
- `notebooklm-py`: available on PyPI (`0.4.0` latest), community/unofficial SDK-style package.
- `nlm`: no standalone PyPI package; command is provided by `notebooklm-cli`.
- NotebookLM MCP/CLI options: community variants exist; not installed in this pass.

## Selection
- Chosen for safe evaluation: `notebooklm-cli` in isolated virtualenv.
- Reason: direct CLI ergonomics, local testability, no Hermes runtime/global install required.

## Isolation
- Virtualenv path: `.venv-notebooklm/`
- No global pip install performed.
- No Hermes production runtime packages modified.

## Verification
- CLI command available: `.venv-notebooklm/bin/nlm`
- Version check: `nlm version 0.1.12`
- Help command works and lists command surface.

## Auth & Secret Handling
- Authentication is interactive via CLI login flow.
- No cookies/tokens/secrets captured or printed.
- No auth material stored in repository files.

## Safety
- Dry-run/report-only posture preserved.
- No Supabase writes added for NotebookLM output.
- `HERMES_KNOWLEDGE_AUTO_STORE_ENABLED` unchanged.
