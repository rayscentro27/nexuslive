#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from revenue_engine.revenue_experiment_tracker import build_experiment_record
from revenue_engine.revenue_foundation import (
    build_revenue_dashboard_stub,
    load_revenue_foundation_config,
    suggest_revenue_bundle,
)


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def main() -> int:
    ok = True
    cfg = load_revenue_foundation_config()
    stub = build_revenue_dashboard_stub()
    bundle = suggest_revenue_bundle("SBA line of credit support", "funding")
    rec = build_experiment_record("Credit improvement system", "credit", 0.77)

    ok &= check("config loads", isinstance(cfg, dict) and bool(cfg))
    ok &= check("beehiiv config exists", (cfg.get("newsletter") or {}).get("provider") == "beehiiv")
    ok &= check("newsletter name exists", bool((cfg.get("newsletter") or {}).get("name")))
    ok &= check("affiliate stack exists", len(cfg.get("affiliate_offers") or []) >= 20)
    categories = {str(a.get("category")) for a in (cfg.get("affiliate_offers") or [])}
    ok &= check("affiliate categories exist", len(categories) >= 5)
    placeholder_only = all((a.get("tracking_id") == "AFFILIATE_ID_PLACEHOLDER") for a in (cfg.get("affiliate_offers") or []))
    ok &= check("placeholder tracking fields only", placeholder_only)
    ok &= check("lead magnets exist", len(cfg.get("lead_magnets") or []) >= 4)
    ok &= check("mini tools exist", len(cfg.get("ai_mini_tools") or []) >= 4)
    ok &= check("digital products exist", len(cfg.get("digital_products") or []) >= 3)
    ok &= check("dashboard stub read-only", stub.get("read_only") is True)
    ok &= check("bundle has affiliate suggestion", bool(bundle.get("affiliate_partner")))
    ok &= check("no fake revenue numbers in stub", "revenue" not in " ".join(stub.keys()).lower())
    ok &= check("no hardcoded affiliate IDs", "http" not in str(cfg.get("affiliate_offers")))

    constraints = rec.get("constraints") or {}
    ok &= check("paid ads autopublish false", constraints.get("paid_ads_autopublish") is False)
    ok &= check("auto spend false", constraints.get("auto_spend_enabled") is False)
    ok &= check("auto payment processing false", constraints.get("auto_payment_processing") is False)
    ok &= check("real payment flows false", constraints.get("real_payment_flows_enabled") is False)

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
