# Mac Mini Health & Safe Mode

Two standalone scripts for local Mac Mini safety diagnostics:

## scripts/macmini_health.sh

Read-only health overview: system load, memory pressure, disk, thermal
status, top memory consumers, Nexus/Hermes/Chosen processes, launchd jobs,
non-Nexus python/node processes, and listening ports.

```bash
bash ~/nexus-ai/scripts/macmini_health.sh
```

**Never modifies state.** No services stopped, no processes killed, no files
written outside stdout.

## scripts/macmini_safe_mode.sh

Safe-mode helper that identifies risky local workloads and optionally stops
them. **Defaults to dry-run.** Use explicit flags for other modes.

### Modes

| Flag             | Behavior |
|------------------|----------|
| (none)           | Dry-run — scan and classify processes, show the killable list, do nothing |
| `--dry-run`      | Same as default |
| `--status`       | Read-only system overview (uptime, process counts, launchd) |
| `--apply`        | Show what would be killed — **no-op without `--force`** |
| `--apply --force`| Kill only explicit-allowlist processes (never protected or review) |
| `--help`         | Print usage |

### Classification

Every process is sorted into exactly one of three categories:

- **Protected** (never touched) — matches a protected pattern (below).
- **Review manually** (never auto-killed) — anything not protected and not on
  the explicit killable allowlist, including generic `python`/`node`/`bash`/
  `zsh` interpreters with no build/install context.
- **Killable** (explicit allowlist only) — a script-language process
  (`python`/`node`/`ruby`/`perl`/`bash`/`zsh`) that **also** matches an explicit
  build/install context (`install`, `build`, `compile`, `upload`, `download`,
  `eslint`, `prettier`, `webpack`, `vite`, `tsc`, `jest`, `mocha`, `rspec`).

Generic interpreters are **never** killable on the basis of being an
interpreter — a build/install context match is required.

### Protected processes (never killed)

`nexus`, `hermes`, `chosen`, `thechosenone`, `telegram`, `continuous`,
`operations_center`, `scheduler.py`, `run_nexus_continuous_operations.py`,
`opencode`, `launchd`, plus system processes: `kernel_task`, `syslogd`,
`notifyd`, `configd`, `sshd`, `mds`, `mds_stores`, `Finder`, `Dock`,
`SystemUIServer`, `WindowServer`, `loginwindow`, `opendirectoryd`, `securityd`.

```bash
# Dry-run (default) — no changes
bash ~/nexus-ai/scripts/macmini_safe_mode.sh

# Status overview — read-only
bash ~/nexus-ai/scripts/macmini_safe_mode.sh --status

# Apply preview — shows the allowlist, kills nothing without --force
bash ~/nexus-ai/scripts/macmini_safe_mode.sh --apply

# Apply + force — stop only explicit-allowlist processes
# WARNING: kills processes
bash ~/nexus-ai/scripts/macmini_safe_mode.sh --apply --force
```

## Safety guarantees

- Health script is **read-only**.
- Safe-mode defaults to **dry-run**.
- `--apply` alone is a no-op preview; only `--apply --force` kills, and only
  explicit-allowlist processes — never protected or review-category ones.
- Generic `python`/`node`/`bash`/`zsh` are never killable without a
  build/install context match.
- Protected process list includes Nexus/Hermes/TheChosenOne/Telegram/
  continuous/scheduler patterns by name.
- No launchd edits, no service restarts, no configuration changes.
- No network calls, no secrets read or printed.

## Tests

`tests/test_macmini_scripts.sh` runs 19 lightweight checks: bash syntax,
`--help`/`--status` output, dry-run does not kill, protected patterns present,
health script is read-only, a secrets scan, and a guard that generic
interpreters are not auto-killable.

```bash
bash ~/nexus-ai/tests/test_macmini_scripts.sh
```
