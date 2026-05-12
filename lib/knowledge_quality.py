"""
Knowledge Quality Scoring — Nexus Platform
Scores knowledge records before they enter the Knowledge Brain.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional


# ── constants ─────────────────────────────────────────────────────────────────

QUALITY_HIGH   = "high"
QUALITY_MEDIUM = "medium"
QUALITY_LOW    = "low"
QUALITY_REJECT = "reject"

# Staleness thresholds by domain (days)
STALE_THRESHOLDS: dict[str, int] = {
    "trading":              14,
    "grants":               60,
    "business_opportunities": 90,
    "funding":              30,
    "credit":               60,
    "onboarding":           180,
    "marketing":            30,
    "operations":           7,
    "social":               7,
    "system":               30,
}

TRUSTED_SOURCES = {
    "sbir.gov", "sba.gov", "grants.gov", "usda.gov", "mbda.gov",
    "sec.gov", "finra.org", "federalreserve.gov", "hud.gov",
    "irs.gov", "cfpb.gov", "ftc.gov",
    "nase.org", "ambergrantsforwomen.com", "helloalice.com",
}

HALLUCINATION_RISK_PATTERNS = [
    r"\$[\d,]+(?:k|m|b)? guaranteed",
    r"100%\s+(?:guaranteed|approved|success)",
    r"never\s+(?:fail|rejected|denied)",
    r"instant\s+(?:approval|funding|grant)",
    r"no\s+credit\s+check\s+required",
]


# ── data structures ────────────────────────────────────────────────────────────

@dataclass
class QualityScore:
    source_reliability: int       # 0–25
    freshness: int                # 0–25
    completeness: int             # 0–25
    operational_usefulness: int   # 0–15
    hallucination_risk_penalty: int  # 0–10 (subtracted)
    duplicate_risk_penalty: int   # 0–5  (subtracted)

    quality_score: int = field(init=False)
    quality_label: str = field(init=False)
    reasons: list[str] = field(default_factory=list)
    recommended_action: str = field(default_factory=str)

    def __post_init__(self):
        raw = (
            self.source_reliability
            + self.freshness
            + self.completeness
            + self.operational_usefulness
            - self.hallucination_risk_penalty
            - self.duplicate_risk_penalty
        )
        self.quality_score = max(0, min(100, raw))

        if self.quality_score >= 70:
            self.quality_label = QUALITY_HIGH
            self.recommended_action = "approve"
        elif self.quality_score >= 45:
            self.quality_label = QUALITY_MEDIUM
            self.recommended_action = "approve_with_caution"
        elif self.quality_score >= 20:
            self.quality_label = QUALITY_LOW
            self.recommended_action = "manual_review_required"
        else:
            self.quality_label = QUALITY_REJECT
            self.recommended_action = "reject"


# ── scoring functions ─────────────────────────────────────────────────────────

def _score_source_reliability(source_url: Optional[str]) -> tuple[int, list[str]]:
    reasons: list[str] = []
    if not source_url:
        reasons.append("No source URL provided")
        return 5, reasons

    url_lower = source_url.lower()
    for domain in TRUSTED_SOURCES:
        if domain in url_lower:
            reasons.append(f"Trusted government/nonprofit source: {domain}")
            return 25, reasons

    if ".gov" in url_lower:
        reasons.append("Government (.gov) source")
        return 22, reasons
    if ".edu" in url_lower:
        reasons.append("Educational (.edu) source")
        return 18, reasons
    if "https://" in url_lower:
        reasons.append("HTTPS source present")
        return 12, reasons

    reasons.append("Unverified or HTTP source")
    return 7, reasons


def _score_freshness(
    domain: str,
    created_at: Optional[datetime],
    last_verified_at: Optional[datetime],
) -> tuple[int, list[str]]:
    reasons: list[str] = []
    threshold_days = STALE_THRESHOLDS.get(domain, 30)
    now = datetime.now(timezone.utc)

    reference = last_verified_at or created_at
    if not reference:
        reasons.append("No timestamp — freshness unknown")
        return 5, reasons

    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)

    age_days = (now - reference).days
    if age_days <= threshold_days // 4:
        reasons.append(f"Very fresh: {age_days} days old")
        return 25, reasons
    if age_days <= threshold_days // 2:
        reasons.append(f"Fresh: {age_days} days old")
        return 18, reasons
    if age_days <= threshold_days:
        reasons.append(f"Acceptable: {age_days} days old (threshold: {threshold_days})")
        return 12, reasons

    reasons.append(f"Stale: {age_days} days old (threshold: {threshold_days})")
    return 3, reasons


def _score_completeness(content: str) -> tuple[int, list[str]]:
    reasons: list[str] = []
    if not content or len(content.strip()) < 50:
        reasons.append("Content too short (<50 chars)")
        return 2, reasons

    score = 0
    length = len(content)
    if length >= 500:
        score += 8
        reasons.append(f"Good length ({length} chars)")
    elif length >= 200:
        score += 5
        reasons.append(f"Adequate length ({length} chars)")
    else:
        score += 2
        reasons.append(f"Short content ({length} chars)")

    if any(kw in content.lower() for kw in ["amount", "deadline", "eligibility", "url", "source", "apply"]):
        score += 9
        reasons.append("Contains key structured fields")
    if re.search(r"https?://", content):
        score += 5
        reasons.append("Contains source URL")
    if any(kw in content.lower() for kw in ["strategy", "entry", "exit", "risk", "grant", "funding", "business"]):
        score += 3
        reasons.append("Domain-relevant content detected")

    return min(25, score), reasons


def _score_usefulness(domain: str, content: str) -> tuple[int, list[str]]:
    reasons: list[str] = []
    domain_keywords = {
        "trading":               ["strategy", "entry", "exit", "backtest", "signal", "stop loss", "take profit"],
        "grants":                ["grant", "award", "eligibility", "deadline", "apply", "sbir", "federal"],
        "business_opportunities": ["startup", "revenue", "business", "launch", "opportunity"],
        "funding":               ["loan", "credit", "funding", "approval", "lender", "sba"],
        "credit":                ["credit score", "dispute", "tradeline", "repair", "utilization"],
        "onboarding":            ["setup", "onboard", "welcome", "guide", "first step"],
        "operations":            ["deploy", "server", "service", "monitor", "alert"],
    }
    keywords = domain_keywords.get(domain, [])
    if not keywords:
        return 8, ["Generic domain — usefulness not domain-scored"]

    matched = sum(1 for kw in keywords if kw.lower() in content.lower())
    if matched >= 4:
        reasons.append(f"Highly relevant: {matched}/{len(keywords)} domain keywords matched")
        return 15, reasons
    if matched >= 2:
        reasons.append(f"Relevant: {matched}/{len(keywords)} keywords matched")
        return 10, reasons

    reasons.append(f"Low relevance: only {matched}/{len(keywords)} keywords matched")
    return 5, reasons


def _score_hallucination_risk(content: str) -> tuple[int, list[str]]:
    reasons: list[str] = []
    penalty = 0
    for pattern in HALLUCINATION_RISK_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            reasons.append(f"Hallucination risk pattern detected: {pattern[:40]}...")
            penalty += 3
    return min(10, penalty), reasons


def _score_duplicate_risk(content: str, existing_hashes: Optional[list[str]] = None) -> tuple[int, list[str]]:
    reasons: list[str] = []
    if not existing_hashes:
        return 0, reasons
    import hashlib
    content_hash = hashlib.md5(content.strip().lower().encode()).hexdigest()
    if content_hash in existing_hashes:
        reasons.append("Exact duplicate detected")
        return 5, reasons
    return 0, reasons


# ── main scorer ───────────────────────────────────────────────────────────────

def score_knowledge_record(
    content: str,
    domain: str = "operations",
    source_url: Optional[str] = None,
    created_at: Optional[datetime] = None,
    last_verified_at: Optional[datetime] = None,
    existing_hashes: Optional[list[str]] = None,
) -> QualityScore:
    """
    Score a knowledge record before it enters the Knowledge Brain.
    Returns a QualityScore with breakdown, label, and recommended action.
    """
    src_score, src_reasons   = _score_source_reliability(source_url)
    fresh_score, fresh_reasons = _score_freshness(domain, created_at, last_verified_at)
    comp_score, comp_reasons = _score_completeness(content)
    use_score, use_reasons   = _score_usefulness(domain, content)
    hall_pen, hall_reasons   = _score_hallucination_risk(content)
    dup_pen, dup_reasons     = _score_duplicate_risk(content, existing_hashes)

    all_reasons = src_reasons + fresh_reasons + comp_reasons + use_reasons + hall_reasons + dup_reasons

    qs = QualityScore(
        source_reliability=src_score,
        freshness=fresh_score,
        completeness=comp_score,
        operational_usefulness=use_score,
        hallucination_risk_penalty=hall_pen,
        duplicate_risk_penalty=dup_pen,
        reasons=all_reasons,
    )
    return qs


def freshness_status(domain: str, last_verified_at: Optional[datetime]) -> str:
    """Return freshness label for a knowledge record."""
    threshold = STALE_THRESHOLDS.get(domain, 30)
    now = datetime.now(timezone.utc)
    if not last_verified_at:
        return "unknown"
    if last_verified_at.tzinfo is None:
        last_verified_at = last_verified_at.replace(tzinfo=timezone.utc)
    age = (now - last_verified_at).days
    if age <= threshold // 4:
        return "fresh"
    if age <= threshold:
        return "acceptable"
    if age <= threshold * 2:
        return "stale"
    return "expired"
