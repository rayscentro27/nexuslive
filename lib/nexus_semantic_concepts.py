"""
nexus_semantic_concepts.py — Semantic concept expansion for Nexus intelligence retrieval.

Before vector search exists, this gives Hermes conceptual awareness:
- Synonym maps (ICT, grants, funding, business, credit)
- Topic clustering (related concepts to expand queries)
- Scam/hype detection signals
- Source trust scoring
"""

from __future__ import annotations


# ── ICT / Smart Money Concepts ──────────────────────────────────────────────

ICT_CONCEPT_MAP: dict[str, list[str]] = {
    "silver bullet": [
        "ict silver bullet", "silver bullet setup", "fair value gap", "fvg",
        "displacement", "breaker block", "order block", "imbalance",
        "market structure shift", "choch", "break of structure", "bos",
    ],
    "liquidity sweep": [
        "liquidity", "stop hunt", "equal highs", "equal lows", "bsl", "ssl",
        "buyside liquidity", "sellside liquidity", "inducement",
    ],
    "session timing": [
        "london session", "new york session", "ny open", "asian session",
        "killzone", "london open", "new york open", "midnight open",
        "london close", "power of 3", "po3",
    ],
    "ny reversal": [
        "new york reversal", "ny reversal", "am session", "pm session",
        "1030 reversal", "ny am high", "ny am low",
    ],
    "market structure": [
        "market structure", "higher highs", "lower lows", "swing high", "swing low",
        "premium", "discount", "equilibrium", "50% level", "range",
    ],
    "fair value gap": [
        "fair value gap", "fvg", "imbalance", "inefficiency", "gap fill",
        "single candle move", "displacement candle",
    ],
    "order block": [
        "order block", "ob", "breaker block", "mitigation block",
        "bullish ob", "bearish ob", "institutional candle",
    ],
    "entry model": [
        "entry model", "pd array", "price delivery", "optimal trade entry",
        "ote", "fibonacci retracement", "0.618", "0.705",
    ],
}

# ── Grants & Funding Concepts ────────────────────────────────────────────────

GRANTS_CONCEPT_MAP: dict[str, list[str]] = {
    "hello alice": [
        "hello alice grant", "small business grant", "alice grant",
        "hello alice small business", "$10000 grant",
    ],
    "sba grant": [
        "sba", "small business administration", "sba loan", "sba 7a",
        "sba 504", "sba microloan", "sba grant",
    ],
    "cdfi": [
        "cdfi", "community development financial institution", "microloan",
        "community lender", "mission lender", "cdfi microloan",
    ],
    "ai education grant": [
        "ai education grant", "ai education business", "education grant",
        "tech education grant", "stem grant", "ed tech funding",
    ],
    "minority grant": [
        "minority business grant", "minority grant", "mbe grant",
        "woman owned business grant", "wosb", "8a program",
    ],
    "startup funding": [
        "startup grant", "seed funding", "startup capital", "pre-revenue",
        "founder grant", "idea stage funding", "early stage",
    ],
}

FUNDING_CONCEPT_MAP: dict[str, list[str]] = {
    "business line of credit": [
        "business credit line", "revolving credit", "loc", "line of credit",
        "credit facility", "working capital line",
    ],
    "invoice financing": [
        "invoice factoring", "accounts receivable", "ar financing",
        "invoice advance", "factoring",
    ],
    "equipment financing": [
        "equipment loan", "equipment lease", "asset financing",
        "machinery financing", "equipment line",
    ],
    "revenue based financing": [
        "revenue share", "merchant cash advance", "mca", "factor rate",
        "revenue advance", "daily repayment",
    ],
}

BUSINESS_CONCEPT_MAP: dict[str, list[str]] = {
    "ai automation affiliate": [
        "ai affiliate", "ai automation", "affiliate marketing automation",
        "ai tools affiliate", "automation income", "passive income ai",
    ],
    "digital product": [
        "digital product business", "online course", "ebook", "template",
        "notion template", "canva template", "digital download",
    ],
    "agency model": [
        "ai agency", "automation agency", "saas agency", "done for you",
        "dfy", "client acquisition", "retainer model",
    ],
}

CREDIT_CONCEPT_MAP: dict[str, list[str]] = {
    "business credit building": [
        "business credit score", "paydex score", "duns number",
        "net 30 vendor", "business credit cards", "credit building",
        "tradeline", "secured card",
    ],
    "credit utilization": [
        "credit utilization", "utilization ratio", "debt to limit",
        "30% rule", "credit card balance", "revolving utilization",
    ],
    "personal credit": [
        "personal credit score", "fico score", "credit repair",
        "derogatory marks", "collections", "charge off",
        "credit inquiry", "hard pull",
    ],
}

# ── Scam / Hype Detection ────────────────────────────────────────────────────

HYPE_SIGNALS: list[str] = [
    "guaranteed returns", "100% success", "make $10000 overnight",
    "passive income guaranteed", "risk free", "no work required",
    "secret method", "gurus don't want you to know", "copy paste system",
    "done for you cash machine", "set and forget", "automated profits guaranteed",
    "limited time secret", "make money while you sleep guaranteed",
    "instant approval guaranteed", "no credit check guaranteed",
]

SCAM_SIGNALS: list[str] = [
    "wire transfer upfront", "advance fee", "pay to receive grant",
    "government grant fee", "unclaimed grant money", "lottery winner",
    "inheritance transfer", "bitcoin investment guaranteed",
    "forex signal guaranteed", "trading bot guaranteed profit",
]

# ── Source Trust Scoring ─────────────────────────────────────────────────────

SOURCE_TRUST: dict[str, int] = {
    # High trust — official / well-known
    "sba.gov": 95,
    "irs.gov": 95,
    "grants.gov": 95,
    "helloalice.com": 90,
    "investopedia.com": 85,
    "federalreserve.gov": 95,
    "score.org": 85,
    "cdfi.org": 90,
    # Medium trust — established educational
    "youtube.com": 60,
    "udemy.com": 65,
    "coursera.org": 70,
    "skillshare.com": 65,
    # Lower trust — social / unknown
    "twitter.com": 40,
    "tiktok.com": 35,
    "instagram.com": 35,
    "reddit.com": 45,
    "default": 50,
}

# ── Public API ────────────────────────────────────────────────────────────────

ALL_CONCEPT_MAPS: dict[str, dict[str, list[str]]] = {
    "trading": ICT_CONCEPT_MAP,
    "grants": GRANTS_CONCEPT_MAP,
    "funding": FUNDING_CONCEPT_MAP,
    "business": BUSINESS_CONCEPT_MAP,
    "credit": CREDIT_CONCEPT_MAP,
}


def expand_query(query: str, domain: str = "") -> list[str]:
    """
    Given a query string, return a list of semantically related terms.
    Used to broaden Supabase ilike searches before creating research tickets.
    """
    q = query.lower()
    expanded: list[str] = [q]

    maps_to_search = list(ALL_CONCEPT_MAPS.values())
    if domain and domain in ALL_CONCEPT_MAPS:
        maps_to_search = [ALL_CONCEPT_MAPS[domain]] + [m for k, m in ALL_CONCEPT_MAPS.items() if k != domain]

    for concept_map in maps_to_search:
        for concept, synonyms in concept_map.items():
            if concept in q or any(s in q for s in synonyms):
                expanded.extend(synonyms)
                if concept not in expanded:
                    expanded.append(concept)

    return list(dict.fromkeys(expanded))  # deduplicate preserving order


def detect_hype(text: str) -> bool:
    """Returns True if the text contains hype/scam signals."""
    t = text.lower()
    return any(signal in t for signal in HYPE_SIGNALS + SCAM_SIGNALS)


def source_trust_score(url: str) -> int:
    """Returns 0-100 trust score for a URL domain."""
    url_lower = url.lower()
    for domain, score in SOURCE_TRUST.items():
        if domain in url_lower:
            return score
    return SOURCE_TRUST["default"]


def get_related_concepts(topic: str, domain: str = "") -> list[str]:
    """
    Returns top-level concept labels that are related to the topic.
    Used to suggest related research areas in Hermes responses.
    """
    topic_lower = topic.lower()
    related: list[str] = []
    maps_to_search = ALL_CONCEPT_MAPS.items()

    for d, concept_map in maps_to_search:
        for concept, synonyms in concept_map.items():
            if concept in topic_lower or any(s in topic_lower for s in synonyms):
                related.append(concept)

    return list(dict.fromkeys(related))[:5]
