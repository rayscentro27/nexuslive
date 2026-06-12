# TheChoseone Command Guide (read-only context for Hermes Advisor)

TheChoseone (@Nexuschosenbot) executes; Hermes Advisor (@NexusHermesMobileBot)
only **suggests/drafts** commands — it never executes. Source of truth:
`config/thechosenone_commands.json`.

## Status
- `status` — polished system status (services + queue). Use `raw status` for key/values.

## Scouts
- `scouts status` — overview of the 7 scouts.
- `status credit scout` / `status funding scout` / `status opportunity scout` /
  `status trading scout` / `status ai scout` — one scout's status.

## Showroom / approvals
- `what needs approval` — packages awaiting review + exact approve/revise commands.
- `show package <id>` — a package's assets + status.
- `approve all assets in package <id> with notes: <notes>` — batch-approve for
  **manual use/review** (NOT auto-publish/send/charge).
- `request revision for package <id> with notes: <notes>` — send back for revision.

## Proof automation
- `run proof automation test` — queue a run (internal; honest receipt).
- `what did nexus produce` — assets produced by track.

## Research queue
- `status research queue` — monetization/keyword research status.
- `run web research: <topic>` — queue a web-research task (Advisor drafts; logged).

## Daily reports
- `daily report` — daily operations summary.

## Safety controls
- `stop sends` · `stop trading` · `pause automation` · `resume automation`.

## Worker / Codex / Claude / OpenCode tasks
- `task for codex: <prompt>` / `task for claude: <prompt>` / `task for opencode: <prompt>`
  — queues the task. **Today the CLI bridge is OFF**, so it queues + prepares a
  copy/paste prompt (no live agent execution).

## Trading (demo / read-only)
- Trading is demo/practice only. `stop trading` halts tests; no live/funded trading.

## Advisor commands (Hermes Mobile)
- `Hermes, <question>` or `@NexusHermesMobileBot <question>` — strategy, explanations,
  command drafts, research. Read-only; proposes, never executes.

## How Hermes Advisor should answer command questions
1. Explain briefly. 2. Draft the **exact** command. 3. Say it executes (TheChoseone)
or only proposes (Advisor). 4. Never execute it. Approval = manual-use approval only.
