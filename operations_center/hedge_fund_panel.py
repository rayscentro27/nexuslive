#!/usr/bin/env python3
"""
Nexus AI Hedge Fund Panel
Reads strategy candidates and generates signal proposals.
SIGNAL ONLY — DRY_RUN=TRUE — no broker execution.
"""
import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
except ImportError:
    pass

logger = logging.getLogger("HedgeFundPanel")

DRY_RUN = True  # NEVER set to False without explicit broker config + legal review
STRATEGIES_DIR = Path(__file__).parent.parent / "research-engine" / "strategies"
SIGNALS_FILE = Path(__file__).parent / "signals_log.json"

SENTIMENT_KEYWORDS = {
    "bullish": ["breakout", "uptrend", "long", "buy", "support", "rally", "momentum", "reversal up"],
    "bearish": ["breakdown", "downtrend", "short", "sell", "resistance", "crash", "distribution"],
    "neutral": ["sideways", "range", "consolidation", "wait", "uncertain"],
}


def _load_signals() -> List[Dict]:
    if SIGNALS_FILE.exists():
        try:
            return json.loads(SIGNALS_FILE.read_text())
        except Exception:
            pass
    return []


def _save_signals(signals: List[Dict]):
    SIGNALS_FILE.write_text(json.dumps(signals[-200:], indent=2, default=str))


def score_sentiment(text: str) -> Dict[str, Any]:
    text_lower = text.lower()
    scores = {k: sum(1 for w in words if w in text_lower)
              for k, words in SENTIMENT_KEYWORDS.items()}
    dominant = max(scores, key=scores.get)
    total = sum(scores.values()) or 1
    confidence = round(scores[dominant] / total * 100)
    return {"sentiment": dominant, "confidence": confidence, "raw": scores}


def extract_signal_candidate(title: str, content: str) -> Dict[str, Any]:
    """Parse a strategy summary into a structured signal candidate."""
    sentiment = score_sentiment(content)

    # Pull any lines that look like explicit strategy instructions
    strategy_lines = [
        line.strip() for line in content.splitlines()
        if any(kw in line.lower() for kw in
               ["entry", "exit", "stop", "target", "setup", "trigger", "risk", "r:r", "r/r"])
        and len(line.strip()) > 20
    ]

    return {
        "id": f"SIG-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "source": title,
        "sentiment": sentiment["sentiment"],
        "confidence": sentiment["confidence"],
        "strategy_notes": strategy_lines[:5],
        "dry_run": True,
        "generated_at": datetime.now().isoformat(),
    }


def generate_signals(limit: int = 10) -> List[Dict]:
    """Generate signal candidates from latest strategy files."""
    files = sorted(STRATEGIES_DIR.glob("*.summary"),
                   key=lambda f: f.stat().st_mtime, reverse=True)[:limit]

    candidates = []
    for f in files:
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
            title = f.stem.replace(".en.vtt", "")
            sig = extract_signal_candidate(title, content)
            candidates.append(sig)
        except Exception as e:
            logger.warning(f"Could not process {f.name}: {e}")

    # Persist
    existing = _load_signals()
    existing.extend(candidates)
    _save_signals(existing)

    logger.info(f"Generated {len(candidates)} signal candidates (DRY_RUN={DRY_RUN})")
    return candidates


def get_recent_signals(n: int = 20) -> List[Dict]:
    return _load_signals()[-n:]


def get_market_sentiment_summary() -> Dict[str, Any]:
    """Aggregate sentiment across all strategy files."""
    files = list(STRATEGIES_DIR.glob("*.summary"))
    if not files:
        return {"status": "no_data", "files": 0}

    totals = {"bullish": 0, "bearish": 0, "neutral": 0}
    for f in files:
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
            s = score_sentiment(content)
            totals[s["sentiment"]] += 1
        except Exception:
            pass

    total = sum(totals.values()) or 1
    dominant = max(totals, key=totals.get)
    return {
        "dominant": dominant,
        "bullish_pct": round(totals["bullish"] / total * 100),
        "bearish_pct": round(totals["bearish"] / total * 100),
        "neutral_pct": round(totals["neutral"] / total * 100),
        "files_analyzed": len(files),
        "updated": datetime.now().isoformat(),
    }


def get_panel_data() -> Dict[str, Any]:
    return {
        "dry_run": DRY_RUN,
        "market_sentiment": get_market_sentiment_summary(),
        "recent_signals": get_recent_signals(10),
        "strategy_count": len(list(STRATEGIES_DIR.glob("*.summary"))),
    }


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser()
    p.add_argument("--generate", action="store_true")
    p.add_argument("--status", action="store_true")
    args = p.parse_args()
    if args.generate:
        sigs = generate_signals()
        print(json.dumps(sigs, indent=2, default=str))
    else:
        print(json.dumps(get_panel_data(), indent=2, default=str))
