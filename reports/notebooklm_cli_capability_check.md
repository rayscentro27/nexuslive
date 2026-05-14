# NotebookLM CLI Capability Check

- Timestamp: 2026-05-14 UTC
- CLI binary detected: `.venv-notebooklm/bin/nlm`
- CLI version: `nlm 0.1.12`
- Authentication status: not authenticated (`nlm auth status` reports missing default profile)

## Verified CLI capabilities

- Notebook listing by name is supported (`nlm notebook list --json`)
- Notebook detail retrieval is supported (`nlm notebook get <id> --json`)
- Notebook summary/digest retrieval is supported (`nlm notebook describe <id>`)
- Source listing is supported (`nlm source list <notebook_id> --json`)
- Source detail retrieval is supported (`nlm source get <source_id> --json`)

## Safety notes

- No auth/session secrets were exposed or persisted.
- No live trading flags were modified.
