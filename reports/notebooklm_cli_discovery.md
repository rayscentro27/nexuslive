# NotebookLM CLI Discovery

## Safe Discovery Commands Run
- `python3 scripts/nexus_notebooklm_ops.py discover`

## Findings
- CLI binary detected at `.venv-notebooklm/bin/nlm`.
- CLI help works headless (`headless_help_ok=true`).
- Auth status: not authenticated.
- Notebook/source command capabilities are available (`--json` support detected).
- Current blocker is auth profile setup, not CLI installation.

## Auth/Headless Notes
- CLI reports: `Profile not found: default`.
- Required next operator command: `nlm login` from the NotebookLM virtualenv context.
- No credentials/tokens were printed or stored in this pass.

## Env/Config
- Supabase env remains external and unchanged.
- Registry path for Nexus mapping: `notebooklm/notebook_registry.json`.
