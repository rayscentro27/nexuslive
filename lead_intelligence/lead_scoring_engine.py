#!/usr/bin/env python3
"""
Nexus Lead Intelligence — Lead Scoring Engine
Analyzes incoming leads, scores quality, and triggers Telegram alerts for high-value leads.
"""
import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
except ImportError:
    pass

logger = logging.getLogger("LeadScoring")

LEADS_FILE = Path(__file__).parent / "leads_db.json"

HIGH_VALUE_THRESHOLD = 70  # score out of 100

# Scoring weights
SOURCE_SCORES = {
    "referral":        30,
    "google":          20,
    "instagram":       15,
    "facebook":        15,
    "youtube":         15,
    "direct":          10,
    "cold_outreach":    5,
    "unknown":          5,
}

INTEREST_SCORES = {
    "trading":         25,
    "hedge fund":      25,
    "investment":      20,
    "forex":           20,
    "stocks":          15,
    "crypto":          15,
    "options":         15,
    "portfolio":       15,
    "wealth management": 20,
    "financial planning": 15,
    "consulting":      10,
    "general":          5,
}

INTENT_KEYWORDS = {
    "high": ["ready to invest", "looking to start", "serious", "asap", "urgent",
             "how much", "pricing", "schedule a call", "book", "enroll", "join"],
    "medium": ["interested", "considering", "want to know more", "curious",
                "thinking about", "exploring"],
    "low": ["just browsing", "maybe", "not sure", "someday"],
}


def _load_leads() -> List[Dict]:
    if LEADS_FILE.exists():
        try:
            return json.loads(LEADS_FILE.read_text())
        except Exception:
            pass
    return []


def _save_leads(leads: List[Dict]):
    LEADS_FILE.write_text(json.dumps(leads, indent=2, default=str))


def score_lead(
    name: str,
    email: str = "",
    phone: str = "",
    source: str = "unknown",
    interest: str = "general",
    message: str = "",
    budget: Optional[str] = None,
) -> Dict[str, Any]:
    """Score a lead from 0-100."""
    score = 0
    reasons = []

    # Source score
    src_score = SOURCE_SCORES.get(source.lower(), 5)
    score += src_score
    reasons.append(f"Source ({source}): +{src_score}")

    # Interest score
    int_score = 0
    for kw, pts in INTEREST_SCORES.items():
        if kw in interest.lower() or kw in message.lower():
            int_score = max(int_score, pts)
    score += int_score
    if int_score:
        reasons.append(f"Interest match: +{int_score}")

    # Contact completeness
    if email:
        score += 10
        reasons.append("Has email: +10")
    if phone:
        score += 10
        reasons.append("Has phone: +10")

    # Intent from message
    msg_lower = message.lower()
    intent_level = "low"
    for level, keywords in INTENT_KEYWORDS.items():
        if any(kw in msg_lower for kw in keywords):
            intent_level = level
            break

    intent_pts = {"high": 20, "medium": 10, "low": 0}[intent_level]
    score += intent_pts
    if intent_pts:
        reasons.append(f"Intent ({intent_level}): +{intent_pts}")

    # Budget signal
    if budget:
        try:
            bval = float(budget.replace(",", "").replace("$", "").strip())
            if bval >= 50000:
                score += 15
                reasons.append(f"High budget (${bval:,.0f}): +15")
            elif bval >= 10000:
                score += 8
                reasons.append(f"Medium budget (${bval:,.0f}): +8")
        except Exception:
            pass

    score = min(score, 100)
    tier = "high" if score >= HIGH_VALUE_THRESHOLD else "medium" if score >= 40 else "low"

    return {
        "score": score,
        "tier": tier,
        "intent": intent_level,
        "reasons": reasons,
        "is_high_value": score >= HIGH_VALUE_THRESHOLD,
    }


def add_lead(
    name: str,
    email: str = "",
    phone: str = "",
    source: str = "unknown",
    interest: str = "general",
    message: str = "",
    budget: Optional[str] = None,
) -> Dict[str, Any]:
    """Add a lead and score it."""
    scoring = score_lead(name, email, phone, source, interest, message, budget)

    lead = {
        "id": f"LEAD-{datetime.now().strftime('%Y%m%d%H%M%S%f')[:18]}",
        "name": name,
        "email": email,
        "phone": phone,
        "source": source,
        "interest": interest,
        "message": message,
        "budget": budget,
        "created_at": datetime.now().isoformat(),
        **scoring,
    }

    leads = _load_leads()
    leads.append(lead)
    _save_leads(leads)

    if lead["is_high_value"]:
        logger.info(f"🔥 HIGH-VALUE LEAD: {name} (score={lead['score']}, source={source})")

    return lead


def get_lead_summary() -> Dict[str, Any]:
    leads = _load_leads()
    if not leads:
        return {"total": 0, "high_value": 0, "medium": 0, "low": 0, "recent": []}

    high = [l for l in leads if l.get("tier") == "high"]
    med  = [l for l in leads if l.get("tier") == "medium"]
    low  = [l for l in leads if l.get("tier") == "low"]

    source_dist = {}
    for l in leads:
        s = l.get("source", "unknown")
        source_dist[s] = source_dist.get(s, 0) + 1

    recent = sorted(leads, key=lambda x: x.get("created_at", ""), reverse=True)[:5]

    return {
        "total": len(leads),
        "high_value": len(high),
        "medium": len(med),
        "low": len(low),
        "avg_score": round(sum(l.get("score", 0) for l in leads) / len(leads), 1),
        "source_distribution": source_dist,
        "recent_high_value": high[-5:],
        "recent_leads": recent,
    }


def get_high_value_leads(n: int = 10) -> List[Dict]:
    leads = _load_leads()
    return sorted(
        [l for l in leads if l.get("is_high_value")],
        key=lambda x: x.get("score", 0), reverse=True
    )[:n]


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser()
    p.add_argument("--add", action="store_true")
    p.add_argument("--name", default="Test Lead")
    p.add_argument("--email", default="")
    p.add_argument("--source", default="google")
    p.add_argument("--interest", default="trading")
    p.add_argument("--message", default="I'm interested in your trading program")
    p.add_argument("--status", action="store_true")
    args = p.parse_args()

    if args.add:
        lead = add_lead(args.name, args.email, source=args.source,
                        interest=args.interest, message=args.message)
        print(json.dumps(lead, indent=2))
    else:
        print(json.dumps(get_lead_summary(), indent=2, default=str))
