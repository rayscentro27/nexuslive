#!/usr/bin/env python3
"""
Nexus Reputation Engine — Review Analyzer
Analyzes reviews, scores sentiment, generates suggested responses,
and flags negative reviews for Telegram alerts.
"""
import os
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
except ImportError:
    pass

logger = logging.getLogger("ReviewAnalyzer")

REVIEWS_FILE = Path(__file__).parent / "reviews_db.json"
RESPONSES_FILE = Path(__file__).parent / "suggested_responses.json"

POSITIVE_WORDS = [
    "excellent", "great", "amazing", "fantastic", "outstanding", "perfect",
    "love", "best", "highly recommend", "professional", "helpful", "awesome",
    "wonderful", "superb", "impressive", "brilliant", "exceptional", "top notch",
    "five stars", "5 stars", "knowledgeable", "trustworthy", "reliable",
]
NEGATIVE_WORDS = [
    "terrible", "awful", "horrible", "worst", "bad", "disappointed", "scam",
    "fraud", "waste", "useless", "never again", "rude", "unprofessional",
    "poor", "disgraceful", "incompetent", "liar", "dishonest", "refund",
    "complaint", "disgusting", "unacceptable", "do not use",
]
NEUTRAL_WORDS = ["ok", "okay", "average", "decent", "fine", "alright", "not bad"]


def score_review(text: str) -> Dict[str, Any]:
    """Score a review text for sentiment."""
    text_lower = text.lower()
    pos = sum(1 for w in POSITIVE_WORDS if w in text_lower)
    neg = sum(1 for w in NEGATIVE_WORDS if w in text_lower)
    neu = sum(1 for w in NEUTRAL_WORDS if w in text_lower)

    if neg > 0 and neg >= pos:
        sentiment = "negative"
        score = max(1, 3 - neg)
    elif pos > neg:
        sentiment = "positive"
        score = min(5, 3 + pos)
    else:
        sentiment = "neutral"
        score = 3

    star_rating = score
    return {
        "sentiment": sentiment,
        "score": score,
        "star_rating": star_rating,
        "positive_signals": pos,
        "negative_signals": neg,
        "flagged": neg >= 2 or ("1 star" in text_lower or "one star" in text_lower),
    }


def generate_response(review: Dict[str, Any]) -> str:
    """Generate a suggested response based on sentiment."""
    sentiment = review.get("sentiment", "neutral")
    source = review.get("source", "Google")
    name = review.get("reviewer_name", "Valued Customer")

    if sentiment == "positive":
        return (
            f"Thank you so much, {name}! We truly appreciate your kind words "
            f"and are thrilled to hear about your positive experience. "
            f"It means a great deal to our team. We look forward to continuing "
            f"to serve you! — The Nexus Team"
        )
    elif sentiment == "negative":
        return (
            f"Dear {name}, we sincerely apologize for your experience and take your "
            f"feedback very seriously. This is not the standard we hold ourselves to. "
            f"Please contact us directly at your earliest convenience so we can make "
            f"this right. We are committed to resolving this for you. — The Nexus Team"
        )
    else:
        return (
            f"Thank you for your feedback, {name}! We appreciate you taking the time "
            f"to share your experience. We're always working to improve and hope to "
            f"exceed your expectations next time. — The Nexus Team"
        )


def _load_reviews() -> List[Dict]:
    if REVIEWS_FILE.exists():
        try:
            return json.loads(REVIEWS_FILE.read_text())
        except Exception:
            pass
    return []


def _save_reviews(reviews: List[Dict]):
    REVIEWS_FILE.write_text(json.dumps(reviews, indent=2, default=str))


def add_review(
    text: str,
    source: str = "manual",
    reviewer_name: str = "Anonymous",
    star_rating: Optional[int] = None,
) -> Dict[str, Any]:
    """Add and analyze a review."""
    analysis = score_review(text)
    if star_rating is not None:
        analysis["star_rating"] = star_rating

    review = {
        "id": f"REV-{datetime.now().strftime('%Y%m%d%H%M%S%f')[:18]}",
        "source": source,
        "reviewer_name": reviewer_name,
        "text": text,
        "analyzed_at": datetime.now().isoformat(),
        "suggested_response": generate_response({**analysis, "source": source, "reviewer_name": reviewer_name}),
        **analysis,
    }

    reviews = _load_reviews()
    reviews.append(review)
    _save_reviews(reviews)

    if review["flagged"]:
        logger.warning(f"⚠️  NEGATIVE REVIEW FLAGGED from {source}: {text[:100]}")

    return review


def get_reputation_summary() -> Dict[str, Any]:
    reviews = _load_reviews()
    if not reviews:
        return {
            "total_reviews": 0,
            "avg_score": 0,
            "positive": 0,
            "negative": 0,
            "neutral": 0,
            "flagged": 0,
            "recent_reviews": [],
        }

    total = len(reviews)
    avg_score = round(sum(r.get("score", 3) for r in reviews) / total, 2)
    sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
    for r in reviews:
        s = r.get("sentiment", "neutral")
        sentiment_counts[s] = sentiment_counts.get(s, 0) + 1

    flagged = [r for r in reviews if r.get("flagged")]
    recent = sorted(reviews, key=lambda r: r.get("analyzed_at", ""), reverse=True)[:5]

    return {
        "total_reviews": total,
        "avg_score": avg_score,
        **sentiment_counts,
        "flagged_count": len(flagged),
        "recent_flagged": flagged[-3:],
        "recent_reviews": recent,
        "top_positive": [r for r in reviews if r.get("sentiment") == "positive"][-3:],
    }


def get_flagged_reviews() -> List[Dict]:
    return [r for r in _load_reviews() if r.get("flagged")]


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser()
    p.add_argument("--add", metavar="TEXT", help="Add a review")
    p.add_argument("--source", default="Google")
    p.add_argument("--name", default="Anonymous")
    p.add_argument("--status", action="store_true")
    args = p.parse_args()

    if args.add:
        r = add_review(args.add, source=args.source, reviewer_name=args.name)
        print(json.dumps(r, indent=2))
    else:
        print(json.dumps(get_reputation_summary(), indent=2, default=str))
