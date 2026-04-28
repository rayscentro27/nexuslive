# Coordination Workflow

This workspace now has a shared coordination layer backed by Supabase:

- `coord_activity` — agents log file changes and notable actions
- `coord_tasks` — tasks can be posted, claimed, and completed
- `coord_context` — shared key/value state across agents
- `nexus_coord.py` — terminal CLI for Codex, Claude Code, and Hermes

## Codex / VS Code Prompt

At the start of each session, run:

```bash
python3 /Users/raymonddavis/nexus-ai/nexus_coord.py tasks codex
```

When you finish editing a file, run:

```bash
python3 /Users/raymonddavis/nexus-ai/nexus_coord.py log codex modified "Updated <description>" <file_path>
```

When you complete a task:

```bash
python3 /Users/raymonddavis/nexus-ai/nexus_coord.py task-done <task_id>
```

Optional: when you explicitly pick up a posted task:

```bash
python3 /Users/raymonddavis/nexus-ai/nexus_coord.py task-claim <task_id> codex
```

## Hermes / Telegram Phrases

Use Hermes language like:

- `show activity`
- `coordination summary`
- `assign task to codex: <description>`
- `assign task to claude: <description>`
- `show tasks for codex`

## Useful CLI Commands

```bash
python3 nexus_coord.py summary
python3 nexus_coord.py activity --limit 20
python3 nexus_coord.py activity --limit 20 --agent codex
python3 nexus_coord.py tasks codex
python3 nexus_coord.py add-task codex "Review launchd runtime" "Verify recovery behavior" --priority high
python3 nexus_coord.py set-context active_focus "coordination rollout" codex
```

## Agent Names

The CLI accepts a few friendly aliases:

- `codex`
- `claude` → stored as `claude-code`
- `hermes`
- `all`
