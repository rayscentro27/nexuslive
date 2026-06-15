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

| Flag        | Behavior |
|-------------|----------|
| (none)      | Dry-run — scan processes, show what would be killed, do nothing |
| `--dry-run` | Same as default |
| `--status`  | Read-only system overview (uptime, process counts, launchd) |
| `--apply`   | Kill non-allowlisted python/node/ruby/perl processes |
| `--help`    | Print usage |

### Protected processes (never killed)

Nexus, Hermes, TheChoseone, python.*nexus, python.*hermes, plus system
processes: launchd, kernel_task, syslogd, notifyd, configd, sshd, mds,
mds_stores, Finder, Dock, SystemUIServer, WindowServer, loginwindow,
opendirectoryd, securityd.

### Killable processes (only when not protected)

Python, Node, Ruby, Perl processes that do not match any protected pattern.

```bash
# Dry-run (default) — no changes
bash ~/nexus-ai/scripts/macmini_safe_mode.sh

# Status overview — read-only
bash ~/nexus-ai/scripts/macmini_safe_mode.sh --status

# Apply — stop risky non-Nexus workloads
# WARNING: kills processes
bash ~/nexus-ai/scripts/macmini_safe_mode.sh --apply
```

## Safety guarantees

- Health script is **read-only**.
- Safe-mode defaults to **dry-run**.
- `--apply` is **explicit** and displays a warning banner.
- Protected process list includes Nexus/Hermes/TheChoseone by name.
- No launchd edits, no service restarts, no configuration changes.
- No network calls, no secrets read or printed.
