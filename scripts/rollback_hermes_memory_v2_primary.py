"""
rollback_hermes_memory_v2_primary.py
Roll back HERMES_MEMORY_V2_MODE from primary to shadow (safe default).

Usage:
  python scripts/rollback_hermes_memory_v2_primary.py --dry-run
  python scripts/rollback_hermes_memory_v2_primary.py --apply
  python scripts/rollback_hermes_memory_v2_primary.py --apply --restart
  python scripts/rollback_hermes_memory_v2_primary.py --apply --confirm-text "ROLLBACK PRIMARY"

What this does (--apply):
  1. Edits the launchd plist to set HERMES_MEMORY_V2_MODE=shadow
  2. Optionally restarts the Telegram bot service via launchctl

What this does NOT do:
  - Does NOT delete or modify hermes_memory_v2 data
  - Does NOT modify any Supabase tables
  - Does NOT touch old tables
  - Does NOT backfill or migrate records
  - Does NOT delete the approval file (kept for audit)

_SUPABASE_WRITE_ATTEMPTED = False
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

_SUPABASE_WRITE_ATTEMPTED = False  # MUST remain False

ROOT        = Path(__file__).resolve().parent.parent
PLIST_PATH  = Path.home() / "Library" / "LaunchAgents" / "com.raymonddavis.nexus.telegram.plist"
PLIST_LABEL = "com.raymonddavis.nexus.telegram"

REQUIRED_CONFIRM = "ROLLBACK PRIMARY"
TARGET_MODE      = "shadow"


def _get_current_plist_mode() -> str | None:
    """Read HERMES_MEMORY_V2_MODE from the plist file."""
    if not PLIST_PATH.exists():
        return None
    text = PLIST_PATH.read_text(encoding="utf-8")
    m = re.search(
        r"<key>HERMES_MEMORY_V2_MODE</key>\s*<string>([^<]+)</string>",
        text,
    )
    return m.group(1).strip() if m else None


def _set_plist_mode(mode: str) -> None:
    """Replace HERMES_MEMORY_V2_MODE value in the plist file."""
    text = PLIST_PATH.read_text(encoding="utf-8")
    new_text = re.sub(
        r"(<key>HERMES_MEMORY_V2_MODE</key>\s*<string>)[^<]+(</string>)",
        rf"\g<1>{mode}\g<2>",
        text,
    )
    if new_text == text:
        raise RuntimeError(
            "HERMES_MEMORY_V2_MODE key not found in plist — cannot update."
        )
    PLIST_PATH.write_text(new_text, encoding="utf-8")


def _restart_service() -> tuple[bool, str]:
    """Unload then load the launchd service. Returns (ok, message)."""
    try:
        uid = os.getuid()
        subprocess.run(
            ["launchctl", "unload", str(PLIST_PATH)],
            check=False, capture_output=True, timeout=15,
        )
        result = subprocess.run(
            ["launchctl", "load", str(PLIST_PATH)],
            check=False, capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            return False, f"launchctl load failed: {result.stderr.strip()}"
        # Verify PID
        ps = subprocess.run(
            ["pgrep", "-f", "telegram_bot.py"],
            capture_output=True, text=True, timeout=5,
        )
        pid = ps.stdout.strip().split("\n")[0] if ps.stdout.strip() else "unknown"
        return True, f"Service restarted. New PID: {pid}"
    except Exception as exc:
        return False, f"restart error: {exc}"


def run(dry_run: bool, restart: bool, confirm_text: str | None) -> int:
    print("=" * 60)
    print("HERMES MEMORY V2 PRIMARY ROLLBACK")
    print("=" * 60)
    print()

    if not dry_run and confirm_text is not None:
        if confirm_text.strip() != REQUIRED_CONFIRM:
            print(f"ERROR: --confirm-text must be exactly: {REQUIRED_CONFIRM!r}")
            print(f"       Got: {confirm_text!r}")
            return 1

    # Check plist exists
    if not PLIST_PATH.exists():
        print(f"ERROR: Plist not found: {PLIST_PATH}")
        return 1

    current_mode = _get_current_plist_mode()
    print(f"Current HERMES_MEMORY_V2_MODE in plist: {current_mode!r}")
    print(f"Target  HERMES_MEMORY_V2_MODE:           {TARGET_MODE!r}")
    print()

    if current_mode == TARGET_MODE:
        print(f"Already set to {TARGET_MODE!r}. Nothing to do.")
        return 0

    if dry_run:
        print("[DRY RUN] Would update plist:")
        print(f"  {PLIST_PATH}")
        print(f"  HERMES_MEMORY_V2_MODE: {current_mode!r} -> {TARGET_MODE!r}")
        if restart:
            print("[DRY RUN] Would restart: launchctl unload/load plist")
        print()
        print("Run with --apply to execute.")
        return 0

    # Apply
    print("Applying rollback...")
    _set_plist_mode(TARGET_MODE)
    print(f"  Plist updated: HERMES_MEMORY_V2_MODE={TARGET_MODE!r}")

    if restart:
        ok, msg = _restart_service()
        if ok:
            print(f"  {msg}")
        else:
            print(f"  WARNING: {msg}")
            print("  Plist was updated — restart manually:")
            print(f"    launchctl unload {PLIST_PATH}")
            print(f"    launchctl load   {PLIST_PATH}")

    print()
    print("Rollback complete.")
    print("  Safety: No Supabase data was modified.")
    print("  Safety: Approval file kept for audit.")
    print("  Verify: send 'show memory v2 shadow status' on Telegram")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="Roll back Memory v2 primary mode to shadow.")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="Preview changes, do not apply.")
    group.add_argument("--apply", action="store_true", help="Apply the rollback.")
    ap.add_argument("--restart", action="store_true", help="Restart Telegram bot after applying.")
    ap.add_argument("--confirm-text", type=str, default=None,
                    help=f"Safety confirmation text (must match {REQUIRED_CONFIRM!r}).")
    args = ap.parse_args()
    sys.exit(run(dry_run=args.dry_run, restart=args.restart, confirm_text=args.confirm_text))


if __name__ == "__main__":
    main()
