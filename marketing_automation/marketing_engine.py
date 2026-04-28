#!/usr/bin/env python3
"""
Nexus AI Marketing Engine
Tracks website leads, reviews, social mentions, and marketing performance.
Outputs sentiment summaries, testimonials, and negative review alerts.
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

logger = logging.getLogger("MarketingEngine")

MENTIONS_FILE = Path(__file__).parent / "mentions_db.json"
INSIGHTS_FILE = Path(__file__).parent / "marketing_insights.json"

PLATFORMS = ["google", "facebook", "instagram", "youtube", "twitter", "website"]

POSITIVE_SIGNALS = [
    "love", "amazing", "great", "recommend", "excellent", "fantastic",
    "awesome", "helpful", "professional", "thank you", "best", "outstanding",
    "incredible", "changed my life", "worth it", "results", "growth",
]
NEGATIVE_SIGNALS = [
    "bad", "terrible", "disappointed", "scam", "fraud", "waste", "refund",
    "awful", "horrible", "not worth", "fake", "misleading", "unprofessional",
]


def _load_mentions() -> List[Dict]:
    if MENTIONS_FILE.exists():
        try:
            return json.loads(MENTIONS_FILE.read_text())
        except Exception:
            pass
    return []


def _save_mentions(mentions: List[Dict]):
    MENTIONS_FILE.write_text(json.dumps(mentions, indent=2, default=str))


def analyze_mention(text: str, platform: str, author: str = "Anonymous") -> Dict[str, Any]:
    """Analyze a social mention or review."""
    text_lower = text.lower()
    pos = sum(1 for w in POSITIVE_SIGNALS if w in text_lower)
    neg = sum(1 for w in NEGATIVE_SIGNALS if w in text_lower)

    if neg > pos:
        sentiment = "negative"
    elif pos > neg:
        sentiment = "positive"
    else:
        sentiment = "neutral"

    is_testimonial = pos >= 2 and neg == 0
    needs_alert = neg >= 1

    mention = {
        "id": f"MEN-{datetime.now().strftime('%Y%m%d%H%M%S%f')[:18]}",
        "platform": platform.lower(),
        "author": author,
        "text": text,
        "sentiment": sentiment,
        "positive_signals": pos,
        "negative_signals": neg,
        "is_testimonial": is_testimonial,
        "needs_alert": needs_alert,
        "recorded_at": datetime.now().isoformat(),
    }

    mentions = _load_mentions()
    mentions.append(mention)
    _save_mentions(mentions)

    if needs_alert:
        logger.warning(f"⚠️ NEGATIVE MENTION on {platform}: {text[:80]}")
    elif is_testimonial:
        logger.info(f"⭐ TESTIMONIAL on {platform}: {text[:80]}")

    return mention


def get_marketing_summary() -> Dict[str, Any]:
    mentions = _load_mentions()
    if not mentions:
        return {
            "total_mentions": 0,
            "sentiment": {"positive": 0, "negative": 0, "neutral": 0},
            "platform_breakdown": {},
            "testimonials": [],
            "negative_alerts": [],
            "top_insights": [],
        }

    by_sentiment = {"positive": 0, "negative": 0, "neutral": 0}
    by_platform = {}
    testimonials = []
    alerts = []

    for m in mentions:
        s = m.get("sentiment", "neutral")
        by_sentiment[s] = by_sentiment.get(s, 0) + 1

        p = m.get("platform", "unknown")
        by_platform[p] = by_platform.get(p, 0) + 1

        if m.get("is_testimonial"):
            testimonials.append(m)
        if m.get("needs_alert"):
            alerts.append(m)

    total = len(mentions)
    pos_pct = round(by_sentiment["positive"] / total * 100)
    neg_pct = round(by_sentiment["negative"] / total * 100)

    insights = []
    if pos_pct >= 70:
        insights.append(f"Strong positive reputation: {pos_pct}% positive mentions")
    if neg_pct >= 20:
        insights.append(f"⚠️ High negative rate: {neg_pct}% — review needed")
    top_platform = max(by_platform, key=by_platform.get) if by_platform else "N/A"
    if top_platform != "N/A":
        insights.append(f"Most active platform: {top_platform} ({by_platform[top_platform]} mentions)")

    return {
        "total_mentions": total,
        "sentiment": {
            **by_sentiment,
            "positive_pct": pos_pct,
            "negative_pct": neg_pct,
        },
        "platform_breakdown": by_platform,
        "testimonials": testimonials[-5:],
        "negative_alerts": alerts[-5:],
        "top_insights": insights,
        "updated": datetime.now().isoformat(),
    }


def get_performance_metrics() -> Dict[str, Any]:
    mentions = _load_mentions()
    today = datetime.now().date().isoformat()
    today_mentions = [m for m in mentions if m.get("recorded_at", "").startswith(today)]

    return {
        "total_all_time": len(mentions),
        "today": len(today_mentions),
        "testimonials_total": len([m for m in mentions if m.get("is_testimonial")]),
        "negative_total": len([m for m in mentions if m.get("needs_alert")]),
        "platforms_active": list({m.get("platform") for m in mentions}),
    }


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser()
    p.add_argument("--add", metavar="TEXT")
    p.add_argument("--platform", default="google")
    p.add_argument("--author", default="Anonymous")
    p.add_argument("--status", action="store_true")
    args = p.parse_args()

    if args.add:
        r = analyze_mention(args.add, args.platform, args.author)
        print(json.dumps(r, indent=2))
    else:
        print(json.dumps(get_marketing_summary(), indent=2, default=str))
