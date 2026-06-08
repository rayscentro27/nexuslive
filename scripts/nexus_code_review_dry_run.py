#!/usr/bin/env python3
"""
nexus_code_review_dry_run.py — local, free pre-commit/pre-deploy review (open-code-review style).

Analyzes the current git diff (or staged files) and flags risk WITHOUT auto-fixing or
auto-committing: secrets exposure, Supabase/RLS/migration risk, frontend/deploy risk,
large changes. Recommend-only — a safety net before Claude/Codex/OpenCode output ships.

SAFETY: read-only. No auto-fix, no commit, no deploy. Never prints secret values.
"""
from __future__ import annotations
import argparse, re, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent

SECRET_PAT = re.compile(r"(api[_-]?key|secret|token|password|bearer)\s*[:=]\s*['\"][A-Za-z0-9_\-]{12,}", re.I)
SECRET_LITERAL = re.compile(r"\b(sk-[A-Za-z0-9]{12,}|eyJ[A-Za-z0-9_\-]{20,})")

def git(*a):
    try:
        return subprocess.run(["git", *a], cwd=str(ROOT), capture_output=True, text=True, timeout=30).stdout
    except Exception:
        return ""

def main():
    ap = argparse.ArgumentParser(description="Local code-review dry-run (recommend-only)")
    ap.add_argument("--staged", action="store_true", help="Review staged files only")
    args = ap.parse_args()
    diff = git("diff", "--cached") if args.staged else git("diff")
    files = [l.split("\t")[-1] for l in git("diff", "--name-only", *(["--cached"] if args.staged else [])).splitlines() if l.strip()]
    print("=== Nexus code-review dry-run (recommend-only — no fix, no commit) ===")
    print(f"changed files: {len(files)}")
    risks = []
    # secrets
    sec_hits = [ln for ln in diff.splitlines() if ln.startswith("+") and (SECRET_PAT.search(ln) or SECRET_LITERAL.search(ln))]
    if sec_hits:
        risks.append(f"SECRET EXPOSURE: {len(sec_hits)} added line(s) look like a key/token — DO NOT COMMIT. (values not printed)")
    if any(f.endswith(".env") or "credential" in f.lower() for f in files):
        risks.append("ENV/CREDENTIAL FILE staged — never commit .env or credentials.")
    # supabase / migration / rls
    if any("supabase/migrations" in f for f in files):
        if re.search(r"drop\s+table|drop\s+column|truncate|delete\s+from", diff, re.I):
            risks.append("MIGRATION RISK: destructive SQL (drop/truncate/delete) in a migration — review carefully, additive-only preferred.")
        else:
            risks.append("MIGRATION present — verify additive + RLS policies; needs approval before db push.")
    if re.search(r"enable row level security|create policy|drop policy", diff, re.I):
        risks.append("RLS change detected — confirm admin-only policy matches nexus_os_* convention.")
    # frontend / deploy
    if any(f.startswith("src/") or f.endswith((".tsx",".ts")) for f in files):
        risks.append("FRONTEND change — run `npm run build`; deploy is approval-gated.")
    if any("netlify/functions" in f for f in files):
        risks.append("NETLIFY FUNCTION change — keep under timeout; no secrets in code; deploy approval-gated.")
    # size
    adds = sum(1 for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++"))
    if adds > 400:
        risks.append(f"LARGE CHANGE (+{adds} lines) — consider splitting; review test coverage.")
    print("\nRISKS / SUGGESTIONS:")
    if risks:
        for r in risks: print(f"  • {r}")
    else:
        print("  • none detected (still: run build/tests before deploy).")
    print("\nSuggested checks before shipping:")
    print("  - npm run build (if frontend/function changed)")
    print("  - py_compile changed .py")
    print("  - confirm no .env/secrets staged")
    print("  - deploy/migration require Ray approval")
    print("\nRecommend-only. No files changed, nothing committed or deployed.")

if __name__ == "__main__":
    main()
