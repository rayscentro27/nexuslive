#!/usr/bin/env python3
"""
Nexus Continuous Operations runner.
Coordinates Proof Automation, 7 scouts, Hermes loop, Showroom, Telegram status,
allowlisted email test sender, Instagram DM allowlist adapter, and Oanda
practice/demo read. Modes: one_shot | hourly | daily | continuous_test (default one_shot).

Hard safety: external sends restricted to Ray's allowlist; IG DM queue-only;
Oanda READ-ONLY here (no orders); no public publish/payment/live trading.
Usage: python3 scripts/run_nexus_continuous_operations.py --mode one_shot [--no-send]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import proof_automation as PA          # noqa: E402
from lib import nexus_allowlist as AL            # noqa: E402
from lib import nexus_telegram_ops as TG         # noqa: E402

SCENARIOS = [
    "I need help fixing my credit.",
    "I want business funding but I do not know where to start.",
    "I want to make money online with cleaning products.",
    "I saw a forex strategy on YouTube and want to test it.",
    "Research Postiz and tell me if Nexus should use it.",
]


def _oanda_status() -> dict:
    """Read-only Oanda practice/demo status via the existing safe status script. No orders."""
    try:
        out = subprocess.run([sys.executable, str(ROOT / "scripts" / "trading_autonomy_status.py")],
                             capture_output=True, text=True, timeout=30)
        d = json.loads(out.stdout) if out.stdout.strip().startswith("{") else {}
        eng = d.get("detail", {}).get("engine", {}) or d.get("health", {})
        return {"broker_mode": eng.get("broker_mode"), "live_trading": eng.get("live_trading"),
                "paper_only": eng.get("paper_only"), "execution_mode": eng.get("execution_mode"),
                "oanda_practice_available": eng.get("oanda_practice_available"),
                "open_practice_order_at": eng.get("last_oanda_practice_order_at"),
                "safe_mode": eng.get("safe_mode_active"), "note": "READ-ONLY; no order placed this run"}
    except Exception as e:
        return {"error": str(e)[:100], "note": "status read failed; no order placed"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="one_shot", choices=["one_shot", "hourly", "daily", "continuous_test"])
    ap.add_argument("--no-send", action="store_true", help="draft emails instead of sending")
    args = ap.parse_args()
    actually_send = not args.no_send
    report = {"mode": args.mode, "at": datetime.now(timezone.utc).isoformat()}

    # A. Proof automation simulator
    sims = [PA.simulate(m) for m in SCENARIOS]
    report["simulator"] = [{"track": r["track"], "assets": r["assets"], "package": r["showroom_package"],
                            "metric": r["metric_to_watch"]} for r in sims]

    # B. Scout statuses (plain language)
    report["scouts"] = {sc: TG.scout_status_text(f"{sc} scout") for sc in TG.SCOUTS}

    # D/E. Metrics + showroom
    report["proof_summary"] = PA.summary()

    # 7/9. Allowlisted email test sends — ONE to each allowed address (credit, funding)
    em = []
    em.append(AL.send_allowlisted_email(
        "rayscentro@yahoo.com", "Credit Readiness — your next steps",
        "Here's your credit readiness plan: a readiness assessment, an issue checklist, a dispute/document-prep "
        "checklist, and a 30-day action plan. Educational guidance only — no guaranteed score increase or deletion.",
        template="credit_readiness_info", project="continuous_ops_test", actually_send=actually_send))
    em.append(AL.send_allowlisted_email(
        "goclearonline@gmail.com", "Business Funding Readiness — your next steps",
        "Here's your funding readiness review: a business-foundation checklist, a document-gap list, a bankability "
        "review, and a next-step funding-prep plan. Educational only — no approval guarantee.",
        template="funding_readiness_info", project="continuous_ops_test", actually_send=actually_send))
    # safety check: prove a non-allowlisted address is blocked
    blocked = AL.send_allowlisted_email("stranger@example.com", "should not send", "blocked test",
                                        template="negative_test", actually_send=actually_send)
    report["email"] = {"sends": em, "negative_test_blocked": blocked["status"] == "blocked"}

    # 8. Instagram DM allowlist (queue-only)
    report["instagram"] = AL.queue_or_send_ig_dm(
        "raydavis7677",
        "Nexus test: I can send you the Credit Readiness Checklist, a 30-day action plan, or a funding readiness "
        "review. Which one do you want to test?")

    # 10. Oanda practice read-only
    report["oanda"] = _oanda_status()

    # 11. Telegram plain-language status
    report["telegram_status"] = TG.status_text()

    # write op state
    op = ROOT / "logs" / "proof_automation" / "continuous_ops_latest.json"
    op.write_text(json.dumps(report, indent=2, default=str))
    print(json.dumps({k: (v if k not in ("scouts",) else f"{len(v)} scouts") for k, v in report.items()
                      if k in ("mode", "simulator", "email", "instagram", "oanda", "telegram_status")},
                     indent=2, default=str)[:1800])
    print(f"\n[ops] state: {op.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
