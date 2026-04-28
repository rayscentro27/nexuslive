"""
Landing page copy formatter.

Takes a business recommendation packet plus metadata and turns it into
shorter, market-facing landing page copy blocks that are safer to show to
prospects than raw recommendation text.
"""

from __future__ import annotations

import re
from typing import Dict, List


def _clean(text: str, fallback: str = "") -> str:
    value = re.sub(r"\s+", " ", str(text or "")).strip(" -:;,.")
    return value or fallback


def _strip_article(text: str) -> str:
    return re.sub(r"^(a|an|the)\s+", "", _clean(text), flags=re.IGNORECASE)


def _offer_label(offer: str) -> str:
    normalized = _strip_article(offer).lower()
    if "crm automation" in normalized:
        return "CRM automation offer"
    if "funnel" in normalized:
        return "funnel build offer"
    if "content-to-lead" in normalized or "content to lead" in normalized:
        return "content-to-lead offer"
    return normalized or "growth offer"


def _channel_label(channel: str) -> str:
    normalized = _strip_article(channel).lower()
    if normalized.startswith("repurpose educational content"):
        return "short-form content, lead magnets, and direct outreach"
    return normalized or "one clear acquisition channel"


def _ensure_sentence(text: str) -> str:
    value = _clean(text)
    if not value:
        return ""
    if value.endswith((".", "!", "?")):
        return value
    return value + "."


def _lc(text: str) -> str:
    return _clean(text).rstrip(".").lower()


def _is_simple_start(text: str, prefix: str) -> bool:
    return _lc(text).startswith(prefix.lower())


def _pricing_summary(text: str) -> str:
    normalized = _lc(text)
    if "setup package" in normalized and "monthly retainer" in normalized:
        return "Start with a setup package and add a monthly optimization retainer once the funnel is converting"
    if normalized.startswith("start with"):
        return normalized.capitalize()
    return f"Start with {normalized}"


def _sentence(text: str, fallback: str) -> str:
    value = _clean(text, fallback)
    if not value.endswith((".", "!", "?")):
        value += "."
    return value


def _shorten(text: str, limit: int, fallback: str) -> str:
    value = _clean(text, fallback)
    if len(value) <= limit:
        return value
    clipped = value[:limit].rsplit(" ", 1)[0].strip()
    return clipped or fallback


def format_business_copy(recommendation: dict) -> Dict[str, List[str] | str]:
    metadata = recommendation.get("metadata") or {}
    icp = _clean(metadata.get("icp"), "service businesses that need stronger follow-up")
    offer = _clean(metadata.get("offer"), "a productized growth offer")
    offer_no_article = _strip_article(offer)
    offer_label = _offer_label(offer)
    proof_points = [_clean(x) for x in (metadata.get("proof_points") or []) if _clean(x)]
    pain_points = [_clean(x) for x in (metadata.get("pain_points") or []) if _clean(x)]
    pricing = _clean(metadata.get("pricing_model"), "Simple setup plus monthly retainer pricing")
    acquisition = _clean(metadata.get("acquisition_channel"), "direct outreach and content-led lead generation")
    revenue_model = _clean(metadata.get("revenue_model"), "Productized service revenue with recurring upside")
    acquisition_no_article = _channel_label(acquisition)

    headline = _shorten(
        "Turn missed follow-up into booked calls",
        64,
        "Turn missed follow-up into booked calls",
    )
    subheadline = _ensure_sentence(
        f"For {icp.lower()}, this offer fixes slow follow-up, missed leads, and messy conversion handoffs"
    )
    positioning = _ensure_sentence(
        f"A focused {offer_label} for {icp.lower()}, designed to turn more demand into qualified calls"
    )

    offer_bullets = [
        "Capture inbound leads the moment they arrive.",
        "Automate follow-up so qualified prospects do not go cold.",
        "Centralize pipeline visibility inside one simple CRM workflow.",
        "Turn more demand into booked calls and sales conversations.",
    ]
    proof_bullets = proof_points[:3] or [
        "Clear positioning beats being the best-kept secret.",
        "Visibility matters when buyers are comparing similar offers.",
        "A stronger follow-up system converts more existing demand.",
    ]
    pain_bullets = pain_points[:3] or [
        "Slow follow-up causes warm leads to go cold.",
        "Manual CRM work creates inconsistent conversion.",
        "Owners lose time chasing leads instead of closing them.",
    ]

    who_its_for = _sentence(
        f"This is built for {icp.lower()} who want a simpler way to turn attention into qualified pipeline.",
        "This is built for operators who need a clearer path from attention to pipeline.",
    )
    pricing_blurb = _ensure_sentence(_pricing_summary(pricing))
    cta_label = "Book Your CRM Audit"
    if acquisition_no_article:
        cta_support = _ensure_sentence(
            f"Use {acquisition_no_article.lower()} to drive interest, then route responses into a simple audit, demo, or booking flow"
        )
    else:
        cta_support = "Lead with one clear acquisition channel and route responses into a simple booking flow."

    return {
        "headline": headline,
        "subheadline": subheadline,
        "positioning": positioning,
        "offer_bullets": offer_bullets,
        "proof_bullets": proof_bullets,
        "pain_bullets": pain_bullets,
        "who_its_for": who_its_for,
        "pricing_blurb": pricing_blurb,
        "cta_label": cta_label,
        "cta_support": cta_support,
        "revenue_model": revenue_model,
    }
