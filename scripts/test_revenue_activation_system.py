#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lib.hermes_supabase_first import nexus_knowledge_reply
from lib.revenue_activation_system import (
    affiliate_revenue_map,
    business_audit,
    content_pipeline_status,
    daily_content_suggestions,
    flagship_lead_magnet,
    intelligence_brief_template,
    lead_magnet_catalog,
    today_in_nexus_summary,
    travel_mobile_summary,
)


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def main() -> int:
    ok = True
    p = content_pipeline_status()
    ok &= check("content pipeline status", "pipeline" in p and "next_action" in p)

    leads = lead_magnet_catalog()
    ok &= check("lead magnet catalog", len(leads) >= 5)

    brief = intelligence_brief_template()
    ok &= check("intelligence brief template", len(brief.get("sections") or []) >= 5)

    audit = business_audit({"business_setup_complete": False, "credit_utilization": 47, "automation_stack": False, "newsletter_active": False})
    ok &= check("business audit output", "readiness_score" in audit and isinstance(audit.get("gaps"), list))

    content = daily_content_suggestions()
    ok &= check("daily content suggestions", len(content.get("youtube_ideas") or []) >= 3)

    aff = affiliate_revenue_map("business_funding")
    ok &= check("affiliate map", isinstance(aff.get("affiliate_tieins"), list))

    mob = travel_mobile_summary()
    ok &= check("mobile travel summary", "quick_view" in mob)

    today = today_in_nexus_summary()
    ok &= check("today in nexus summary", "sections" in today and "newsletter_ready" in today)

    magnet = flagship_lead_magnet()
    ok &= check("flagship lead magnet", "Business Funding Readiness Blueprint" in str(magnet.get("name")))

    cmds = [
        nexus_knowledge_reply("How do we make money this week?"),
        nexus_knowledge_reply("What content should we create?"),
        nexus_knowledge_reply("What opportunities look promising?"),
        nexus_knowledge_reply("What did Nexus learn today?"),
        nexus_knowledge_reply("Today in Nexus"),
        nexus_knowledge_reply("Business Funding Readiness Blueprint"),
    ]
    ok &= check("Hermes revenue commands", all(isinstance(c, str) and len(c) > 0 for c in cmds))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
