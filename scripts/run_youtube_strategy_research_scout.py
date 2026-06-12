#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.hermes_email_knowledge_intake import _supabase_get, _supabase_post
from lib.youtube_source_registry import YouTubeSourceRegistry


OUTPUT_JSON = ROOT / "logs" / "youtube_strategy_research_latest.json"
OUTPUT_MD = ROOT / "logs" / "youtube_strategy_research_latest.md"
DISCOVERY_JSON = ROOT / "logs" / "trading_strategy_discovery_latest.json"
DISCOVERY_MD = ROOT / "logs" / "trading_strategy_discovery_latest.md"
SOURCE_CONFIG = ROOT / "configs" / "trading_strategy_sources.json"
DEFAULT_URLS_FILE = ROOT / "configs" / "trading_strategy_youtube_urls.txt"
DEFAULT_TRANSCRIPT_PATHS = [
    ROOT / "inbox" / "youtube_transcripts",
    ROOT / "research-engine" / "strategies",
]

FAMILY_KEYWORDS: list[tuple[str, list[str]]] = [
    ("liquidity_sweep", ["liquidity sweep", "sweep", "stop hunt"]),
    ("news_event", ["nfp", "cpi", "fomc", "news trading", "economic release"]),
    ("session_open", ["new york open", "london open", "tokyo open", "opening range", "session open"]),
    ("mean_reversion", ["mean reversion", "bollinger", "fade", "reversion"]),
    ("trend_following", ["trend following", "trend", "pullback", "continuation", "ema crossover", "macd"]),
    ("breakout", ["breakout", "range breakout", "orb", "opening range breakout"]),
    ("technical_indicator", ["rsi", "ema", "sma", "macd", "bollinger", "indicator"]),
    ("hybrid", ["hybrid", "confluence", "context plus technical"]),
]

TIMEFRAME_PATTERNS: list[tuple[str, str]] = [
    (r"\b1 ?minute\b|\b1m\b", "M1"),
    (r"\b5 ?minute\b|\b5m\b", "M5"),
    (r"\b15 ?minute\b|\b15m\b", "M15"),
    (r"\b30 ?minute\b|\b30m\b", "M30"),
    (r"\b1 ?hour\b|\bh1\b|\bhourly\b", "H1"),
    (r"\b4 ?hour\b|\bh4\b", "H4"),
    (r"\bdaily\b|\b1d\b", "D1"),
]

INDICATOR_KEYWORDS = {
    "RSI": ["rsi"],
    "EMA": ["ema", "moving average", "ma crossover"],
    "MACD": ["macd"],
    "Bollinger Bands": ["bollinger"],
    "VWAP": ["vwap"],
    "Opening Range": ["opening range", "orb"],
    "Liquidity Sweep": ["liquidity sweep", "stop hunt", "sweep"],
}

NEGATIVE_STRATEGY_PATTERNS = [
    "no specific trading strategies",
    "does not contain specific trading strategies",
    "no technical indicators were discussed",
    "no explicit risk management techniques",
    "not be directly related to traditional trading strategies",
    "no trade setups",
]

STRATEGY_SIGNAL_TERMS = [
    "strategy",
    "setup",
    "entry",
    "exit",
    "stop loss",
    "take profit",
    "pullback",
    "breakout",
    "mean reversion",
    "liquidity sweep",
    "open",
    "scalp",
    "indicator",
    "risk management",
]

SYMBOL_MAP = {
    "EURUSD": ("forex", ["eurusd", "eur/usd", "euro usd"]),
    "USDJPY": ("forex", ["usdjpy", "usd/jpy", "dollar yen"]),
    "GBPUSD": ("forex", ["gbpusd", "gbp/usd", "cable"]),
    "SPY": ("options", ["spy"]),
    "QQQ": ("options", ["qqq", "nasdaq 100"]),
    "BTC": ("crypto", ["btc", "bitcoin"]),
    "ETH": ("crypto", ["eth", "ethereum"]),
}

SEED_TYPE_MAP: list[tuple[str, list[str]]] = [
    ("indicator_seed", ["indicator", "rsi", "ema", "macd", "bollinger", "oscillator", "vwap"]),
    ("market_structure_seed", ["liquidity", "sweep", "breakout", "range", "session", "open", "price action"]),
    ("strategy_seed", ["strategy", "scalp", "pullback", "trend", "reversion", "setup"]),
    ("research_context", ["macro", "psychology", "news", "cpi", "nfp", "fomc", "risk on", "risk off"]),
]


@dataclass
class SourceDocument:
    source_id: str
    source_type: str
    source_title: str
    source_url: str
    source_channel: str
    raw_text: str
    file_path: str
    asset_class_hint: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_") or "strategy"


def _load_json(path: Path) -> Any:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def _safe_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _load_source_config() -> list[dict[str, Any]]:
    data = _load_json(SOURCE_CONFIG)
    return data if isinstance(data, list) else []


def _parse_structured_transcript(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            header = stripped.lstrip("#").strip().lower()
            if header in {"title", "url", "source type", "related area", "transcript"}:
                current = header
                sections.setdefault(current, [])
                continue
        if current:
            sections[current].append(line)
    return {key: "\n".join(value).strip() for key, value in sections.items()}


def _parse_summary_file(path: Path) -> SourceDocument:
    raw = _safe_text(path)
    stem = path.name.replace(".en.vtt.summary", "").replace(".summary", "")
    if " - " in stem:
        channel, title = stem.split(" - ", 1)
    else:
        channel, title = "", stem
    return SourceDocument(
        source_id="yt_local_" + hashlib.sha256(str(path).encode()).hexdigest()[:12],
        source_type="transcript_summary",
        source_title=title.strip(),
        source_url=f"local://{path.relative_to(ROOT)}",
        source_channel=channel.strip(),
        raw_text=raw,
        file_path=str(path.relative_to(ROOT)),
        asset_class_hint="all",
    )


def _parse_transcript_file(path: Path) -> SourceDocument:
    raw = _safe_text(path)
    sections = _parse_structured_transcript(raw)
    title = sections.get("title") or path.stem.replace("_", " ")
    url = sections.get("url") or f"local://{path.relative_to(ROOT)}"
    channel = ""
    m = re.search(r"youtube\.com/@([A-Za-z0-9_.-]+)", url)
    if m:
        channel = m.group(1)
    return SourceDocument(
        source_id="yt_transcript_" + hashlib.sha256(str(path).encode()).hexdigest()[:12],
        source_type="transcript",
        source_title=title.strip(),
        source_url=url.strip(),
        source_channel=channel,
        raw_text=sections.get("transcript") or raw,
        file_path=str(path.relative_to(ROOT)),
        asset_class_hint="all",
    )


def _load_transcript_documents(paths: list[Path]) -> list[SourceDocument]:
    docs: list[SourceDocument] = []
    for base in paths:
        if base.is_file():
            files = [base]
        elif base.is_dir():
            files = sorted([p for p in base.rglob("*") if p.suffix.lower() in {".md", ".txt", ".summary"} or p.name.endswith(".vtt.summary")])
        else:
            continue
        for path in files:
            if path.name.startswith("."):
                continue
            if path.name.endswith(".summary") or path.name.endswith(".vtt.summary"):
                docs.append(_parse_summary_file(path))
            elif path.suffix.lower() in {".md", ".txt"}:
                docs.append(_parse_transcript_file(path))
    return docs


def _load_urls_file(path: Path) -> list[SourceDocument]:
    docs: list[SourceDocument] = []
    if not path.exists():
        return docs
    registry = YouTubeSourceRegistry()
    for idx, raw_line in enumerate(path.read_text().splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "|" in line:
            url, title = [part.strip() for part in line.split("|", 1)]
        else:
            url, title = line, ""
        source_type = "video" if "watch?v=" in url or "youtu.be/" in url else "channel"
        rec = registry.register(url=url, source_type=source_type, video_title=title)
        docs.append(
            SourceDocument(
                source_id=rec.source_id,
                source_type="url_only",
                source_title=title or f"Manual URL {idx}",
                source_url=url,
                source_channel="",
                raw_text="",
                file_path=str(path.relative_to(ROOT)),
                asset_class_hint="all",
            )
        )
    return docs


def _asset_class_for_symbol(symbol: str) -> str:
    return SYMBOL_MAP.get(symbol, ("unknown", []))[0]


def _extract_symbols(text: str, asset_class_filter: str) -> list[str]:
    lower = text.lower()
    found = [symbol for symbol, (_, terms) in SYMBOL_MAP.items() if any(term in lower for term in terms)]
    if asset_class_filter != "all":
        found = [symbol for symbol in found if _asset_class_for_symbol(symbol) == asset_class_filter]
    return found[:3]


def _seed_type(text: str) -> str:
    lower = text.lower()
    for seed_type, terms in SEED_TYPE_MAP:
        if any(term in lower for term in terms):
            return seed_type
    return "idea_seed"


def _infer_family(text: str) -> str:
    lower = text.lower()
    for family, terms in FAMILY_KEYWORDS:
        if any(term in lower for term in terms):
            return family
    return "technical_indicator"


def _infer_trigger_type(family: str, text: str) -> str:
    lower = text.lower()
    if family == "news_event":
        return "news_calendar_event"
    if family in {"session_open", "breakout"} and any(k in lower for k in ["open", "session", "range"]):
        return "scheduled_session"
    if family == "liquidity_sweep":
        return "liquidity_sweep"
    if "break" in lower:
        return "price_level_break"
    return "continuous_indicator"


def _infer_execution_style(family: str) -> str:
    if family in {"news_event", "session_open"}:
        return "event_window"
    if family in {"liquidity_sweep", "breakout"}:
        return "watcher"
    return "always_on"


def _infer_timeframe(text: str) -> str:
    lower = text.lower()
    for pattern, timeframe in TIMEFRAME_PATTERNS:
        if re.search(pattern, lower):
            return timeframe
    if "scalp" in lower:
        return "M5"
    return "H1"


def _extract_indicators(text: str) -> list[str]:
    lower = text.lower()
    out = [name for name, terms in INDICATOR_KEYWORDS.items() if any(term in lower for term in terms)]
    return out[:6]


def _infer_preferred_side(text: str, family: str) -> str:
    lower = text.lower()
    if any(term in lower for term in ["sell", "short", "bearish"]):
        return "SELL"
    if any(term in lower for term in ["buy", "long", "bullish"]):
        return "BUY"
    if family in {"mean_reversion", "liquidity_sweep"}:
        return "SELL"
    return "BUY"


def _build_rule_templates(strategy_name: str, family: str, trigger_type: str, symbol: str, timeframe: str, text: str) -> dict[str, Any]:
    lower = text.lower()
    side = _infer_preferred_side(text, family)
    entry = f"Watch {symbol} on {timeframe}. Trigger a {side.lower()} when the {strategy_name.replace('_', ' ')} setup confirms."
    exit_rule = "Exit on opposite confirmation, failed follow-through, or at the planned reward target."
    stop_rule = "Place stop beyond the setup invalidation level or most recent swing."
    take_profit_rule = "Target at least 1.5R unless the source clearly suggests a different structure."
    session_rule = ""
    news_rule = ""
    invalidation = "Invalidate after loss of trend/session context or if price immediately rejects the setup."
    if family == "session_open":
        session_rule = "Active only around the relevant market open window."
    if trigger_type == "news_calendar_event":
        news_rule = "Active only around the named macro event and only after volatility confirms direction."
    if family == "liquidity_sweep":
        entry = f"Enter after a liquidity sweep and reclaim confirmation on {symbol} {timeframe}."
        invalidation = "Invalidate if the sweep fails to reclaim or the reclaim candle is fully reversed."
    if "opening range" in lower or "orb" in lower:
        session_rule = "Define the opening range first, then act only on breakout or reversion relative to that range."
    return {
        "preferred_side": side,
        "entry_rules": entry,
        "exit_rules": exit_rule,
        "stop_loss_rules": stop_rule,
        "take_profit_rules": take_profit_rule,
        "risk_management_rules": "Paper/demo only. Keep units capped at 1 for forex. Do not force trades without setup confirmation.",
        "session_rules": session_rule or None,
        "news_event_rules": news_rule or None,
        "invalidation_rules": invalidation,
        "required_data": ["candles", "symbol", "timeframe"] + (["session window"] if session_rule else []) + (["economic calendar"] if news_rule else []),
    }


def _summary(text: str) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    if not clean:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", clean)
    return " ".join(sentences[:3])[:900]


def _score_strategy(text: str, family: str, indicators: list[str], symbols: list[str], timeframe: str) -> tuple[float, float, float]:
    lower = text.lower()
    if any(pattern in lower for pattern in NEGATIVE_STRATEGY_PATTERNS):
        return 0.2, 0.25, 0.3
    specificity = 0.25
    if symbols:
        specificity += 0.15
    if timeframe:
        specificity += 0.1
    if family != "technical_indicator":
        specificity += 0.1
    if indicators:
        specificity += min(0.15, 0.05 * len(indicators))
    if any(term in lower for term in ["entry", "stop", "target", "risk", "setup", "breakout", "pullback", "reversion", "liquidity"]):
        specificity += 0.2
    clarity = min(1.0, max(0.35, specificity))
    testability = min(1.0, max(0.3, clarity + (0.15 if len(text) > 400 else 0.0)))
    confidence = min(1.0, max(0.4, (clarity + testability) / 2.0))
    return round(testability, 2), round(clarity, 2), round(confidence, 2)


def _is_strategy_like(text: str) -> bool:
    lower = text.lower()
    if any(pattern in lower for pattern in NEGATIVE_STRATEGY_PATTERNS):
        return any(term in lower for term in ["strategy", "setup", "indicator", "breakout", "scalp", "pullback"])
    return any(term in lower for term in STRATEGY_SIGNAL_TERMS)


def _extract_seed_items(doc: SourceDocument, asset_class_filter: str) -> list[dict[str, Any]]:
    text = f"{doc.source_title}\n{doc.raw_text}"
    lower = text.lower()
    if not any(term in lower for term in STRATEGY_SIGNAL_TERMS):
        return []
    symbols = _extract_symbols(text, asset_class_filter)
    if not symbols:
        inferred = "EURUSD" if asset_class_filter == "forex" else "SPY" if asset_class_filter == "options" else "BTC" if asset_class_filter == "crypto" else "EURUSD"
        symbols = [inferred]
    family = _infer_family(text)
    trigger_type = _infer_trigger_type(family, text)
    seed_type = _seed_type(text)
    timeframe = _infer_timeframe(text)
    indicators = _extract_indicators(text)
    summary = _summary(doc.raw_text or doc.source_title)
    missing_fields: list[str] = []
    if "stop" not in lower:
        missing_fields.append("stop_loss")
    if "take profit" not in lower and "target" not in lower:
        missing_fields.append("take_profit")
    if timeframe == "H1" and not any(re.search(pattern, lower) for pattern, _ in TIMEFRAME_PATTERNS):
        missing_fields.append("timeframe")
    if not indicators and family == "technical_indicator":
        missing_fields.append("indicator_definition")
    if "entry" not in lower and "trigger" not in lower and "breakout" not in lower and "pullback" not in lower:
        missing_fields.append("entry_trigger")
    if "exit" not in lower and "target" not in lower and "stop" not in lower:
        missing_fields.append("exit_rules")

    seeds: list[dict[str, Any]] = []
    for symbol in symbols:
        asset_class = _asset_class_for_symbol(symbol)
        if asset_class_filter != "all" and asset_class != asset_class_filter:
            continue
        seeds.append(
            {
                "seed_id": _slug(f"{symbol}_{doc.source_title}_{seed_type}")[:96],
                "seed_type": seed_type,
                "strategy_family": family,
                "trigger_type": trigger_type,
                "asset_class": asset_class,
                "symbols": [symbol],
                "timeframe_hint": timeframe,
                "indicators_used": indicators,
                "source_url": doc.source_url,
                "source_title": doc.source_title,
                "source_channel": doc.source_channel,
                "raw_summary": summary,
                "missing_fields": missing_fields,
                "research_to_create": [f"define_{field}" for field in missing_fields],
                "variants_to_test": [
                    "session_filter_on_off",
                    "trend_filter_on_off",
                    "atr_stop_1.5",
                    "take_profit_1.5R_2R",
                ],
                "next_safe_action": "generate_variants_and_run_dry_tournament",
                "status": "seed_only" if missing_fields else "seed_ready",
                "source_type": doc.source_type,
                "file_path": doc.file_path,
            }
        )
    return seeds


def _extract_strategies_from_document(doc: SourceDocument, asset_class_filter: str) -> list[dict[str, Any]]:
    text = f"{doc.source_title}\n{doc.raw_text}"
    if not _is_strategy_like(text):
        return []
    symbols = _extract_symbols(text, asset_class_filter)
    if not symbols and asset_class_filter != "all":
        return []
    if not symbols:
        inferred = "EURUSD" if asset_class_filter == "forex" else "SPY" if asset_class_filter == "options" else "BTC" if asset_class_filter == "crypto" else "EURUSD"
        symbols = [inferred]
    family = _infer_family(text)
    trigger_type = _infer_trigger_type(family, text)
    execution_style = _infer_execution_style(family)
    timeframe = _infer_timeframe(text)
    indicators = _extract_indicators(text)
    raw_summary = _summary(doc.raw_text or doc.source_title)
    strategies: list[dict[str, Any]] = []
    for symbol in symbols:
        asset_class = _asset_class_for_symbol(symbol)
        if asset_class_filter != "all" and asset_class != asset_class_filter:
            continue
        strategy_name = doc.source_title or symbol
        strategy_slug = _slug(f"{symbol}_{strategy_name}")[:80]
        rules = _build_rule_templates(strategy_slug, family, trigger_type, symbol, timeframe, text)
        testability, clarity, confidence = _score_strategy(text, family, indicators, [symbol], timeframe)
        status = "testable_candidate" if testability >= 0.65 else "needs_research"
        strategies.append(
            {
                "strategy_id": strategy_slug,
                "strategy_name": strategy_name,
                "asset_class": asset_class,
                "symbols": [symbol],
                "timeframe": timeframe,
                "strategy_family": family,
                "trigger_type": trigger_type,
                "execution_style": execution_style,
                "indicators_used": indicators,
                "entry_rules": rules["entry_rules"],
                "exit_rules": rules["exit_rules"],
                "stop_loss_rules": rules["stop_loss_rules"],
                "take_profit_rules": rules["take_profit_rules"],
                "risk_management_rules": rules["risk_management_rules"],
                "session_rules": rules["session_rules"],
                "news_event_rules": rules["news_event_rules"],
                "invalidation_rules": rules["invalidation_rules"],
                "required_data": rules["required_data"],
                "testability_score": testability,
                "clarity_score": clarity,
                "confidence_score": confidence,
                "source_url": doc.source_url,
                "source_title": doc.source_title,
                "source_channel": doc.source_channel,
                "raw_summary": raw_summary,
                "status": status,
                "preferred_side": rules["preferred_side"],
                "source_type": doc.source_type,
                "file_path": doc.file_path,
            }
        )
    return strategies


def _candidate_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(row.get("source_url") or ""),
        str(row.get("strategy_name") or ""),
        ",".join(row.get("symbols") or []),
        str(row.get("timeframe") or ""),
    )


def _existing_supabase_keys() -> set[tuple[str, str, str, str]]:
    keys: set[tuple[str, str, str, str]] = set()
    for row in _supabase_get("strategy_variants?select=strategy_id,variant_name,parameter_set&limit=500"):
        params = row.get("parameter_set") or {}
        source_url = str(params.get("source_url") or "")
        strategy_name = str(params.get("strategy_name") or row.get("variant_name") or "")
        symbol = str(params.get("symbol") or "")
        timeframe = str(params.get("timeframe") or "")
        if source_url:
            keys.add((source_url, strategy_name, symbol, timeframe))
    return keys


def _write_supabase_variants(rows: list[dict[str, Any]], dry_run: bool) -> tuple[bool, str, int]:
    payloads: list[dict[str, Any]] = []
    for row in rows:
        params = {
            "strategy_name": row["strategy_name"],
            "asset_class": row["asset_class"],
            "symbol": (row.get("symbols") or [""])[0],
            "timeframe": row["timeframe"],
            "strategy_family": row["strategy_family"],
            "trigger_type": row["trigger_type"],
            "execution_style": row["execution_style"],
            "indicators_used": row["indicators_used"],
            "entry_rules": row["entry_rules"],
            "exit_rules": row["exit_rules"],
            "stop_loss_rules": row["stop_loss_rules"],
            "take_profit_rules": row["take_profit_rules"],
            "risk_rules": row["risk_management_rules"],
            "session_rules": row["session_rules"],
            "news_event_rules": row["news_event_rules"],
            "invalidation_rules": row["invalidation_rules"],
            "required_data": row["required_data"],
            "confidence": row["confidence_score"],
            "testability_score": row["testability_score"],
            "clarity_score": row["clarity_score"],
            "status": row["status"],
            "preferred_side": row["preferred_side"],
            "data_quality": "youtube_transcript_extracted",
            "source_url": row["source_url"],
            "source_title": row["source_title"],
            "source_channel": row["source_channel"],
            "source_type": row["source_type"],
            "raw_summary": row["raw_summary"],
            "source_file_path": row["file_path"],
            "source_artifact": str(OUTPUT_JSON.relative_to(ROOT)),
        }
        payloads.append(
            {
                "strategy_id": row["strategy_id"],
                "variant_name": row["strategy_name"],
                "parameter_set": params,
                "backtest_score": round(row["testability_score"] * 100, 2),
                "replay_score": round(row["clarity_score"] * 100, 2),
            }
        )
    if dry_run or not payloads:
        return False, "strategy_variants", 0
    inserted = _supabase_post("strategy_variants", payloads)
    return True, "strategy_variants", len(inserted)


def _match_registry_documents(asset_class_filter: str, registry_rows: list[dict[str, Any]], local_docs: list[SourceDocument]) -> tuple[list[SourceDocument], int, int]:
    matched: list[SourceDocument] = []
    configured_channels = [row for row in registry_rows if row.get("enabled") and row.get("source_type") == "youtube_channel"]
    configured_searches = [row for row in registry_rows if row.get("enabled") and row.get("source_type") == "youtube_search"]
    channel_names = [(str(row.get("name") or "").lower(), str(row.get("asset_class") or "all")) for row in configured_channels]
    keyword_strings = [(kw.lower(), str(row.get("asset_class") or "all")) for row in configured_searches for kw in (row.get("keywords") or [])]
    for doc in local_docs:
        haystack = f"{doc.source_title} {doc.source_channel} {doc.raw_text[:1200]}".lower()
        matched_channel = any(
            channel and channel.split(" channel")[0] in haystack and (asset_class_filter == "all" or configured_asset in {asset_class_filter, "all"})
            for channel, configured_asset in channel_names
        )
        matched_keyword = any(
            keyword in haystack and (asset_class_filter == "all" or configured_asset in {asset_class_filter, "all"})
            for keyword, configured_asset in keyword_strings
        )
        if asset_class_filter != "all" and not matched_channel and not matched_keyword:
            if not any(_asset_class_for_symbol(symbol) == asset_class_filter for symbol in _extract_symbols(haystack, "all")):
                if asset_class_filter not in haystack:
                    continue
        if not _is_strategy_like(haystack):
            continue
        if matched_channel or matched_keyword:
            matched.append(doc)
    deduped: dict[str, SourceDocument] = {doc.source_id: doc for doc in matched}
    return list(deduped.values()), len(configured_channels), len(configured_searches)


def _run_step(cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {
        "command": " ".join(cmd),
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=("registry", "urls", "transcripts"), default="registry")
    parser.add_argument("--asset-class", choices=("all", "forex", "options", "crypto"), default="forex")
    parser.add_argument("--urls-file", default=str(DEFAULT_URLS_FILE))
    parser.add_argument("--transcripts-dir", default=str(DEFAULT_TRANSCRIPT_PATHS[0]))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    registry_rows = _load_source_config()
    registry = YouTubeSourceRegistry()
    local_docs = _load_transcript_documents(DEFAULT_TRANSCRIPT_PATHS)

    if args.source == "registry":
        docs, configured_channels, configured_searches = _match_registry_documents(args.asset_class, registry_rows, local_docs)
    elif args.source == "urls":
        docs = _load_urls_file(Path(args.urls_file))
        configured_channels = 0
        configured_searches = 0
    else:
        docs = _load_transcript_documents([Path(args.transcripts_dir)])
        configured_channels = 0
        configured_searches = 0

    extracted: list[dict[str, Any]] = []
    seeds: list[dict[str, Any]] = []
    for doc in docs:
        if doc.source_url.startswith("http"):
            source_type = "video" if "watch?v=" in doc.source_url or "youtu.be/" in doc.source_url else "channel"
            registry.register(
                url=doc.source_url,
                source_type=source_type,
                channel_name=doc.source_channel,
                video_title=doc.source_title,
                notes="trading_strategy_research_scout",
            )
        extracted.extend(_extract_strategies_from_document(doc, args.asset_class))
        seeds.extend(_extract_seed_items(doc, args.asset_class))

    deduped: list[dict[str, Any]] = []
    duplicates_skipped = 0
    seen: set[tuple[str, str, str, str]] = set()
    existing = set()
    if extracted:
        try:
            existing = _existing_supabase_keys()
        except Exception:
            existing = set()
    for row in extracted:
        key = _candidate_key(row)
        if key in seen or key in existing:
            duplicates_skipped += 1
            continue
        seen.add(key)
        deduped.append(row)

    testable = [row for row in deduped if row["status"] == "testable_candidate"]
    needs_research = [row for row in deduped if row["status"] != "testable_candidate"]
    deduped_seeds: list[dict[str, Any]] = []
    seen_seed_ids: set[str] = set()
    for seed in seeds:
        seed_id = str(seed.get("seed_id") or "")
        if not seed_id or seed_id in seen_seed_ids:
            continue
        seen_seed_ids.add(seed_id)
        deduped_seeds.append(seed)
    rows_written, table_used, rows_inserted = _write_supabase_variants(testable, args.dry_run)

    if testable:
        result_interpretation = "testable_strategies_found"
    elif deduped_seeds:
        result_interpretation = "needs_seed_mode_variant_generation"
    elif docs:
        result_interpretation = "weak_source_quality_or_strict_gate"
    else:
        result_interpretation = "missing_data"

    if testable:
        next_safe_action = "submit testable candidates to dry-run tournament review"
    elif deduped_seeds:
        next_safe_action = "run strategy seed variant generation and dry-run tournament"
    else:
        next_safe_action = "review approved channels and add stronger manual URLs/transcripts"

    handoff_steps = {
        "supabase_strategy_search": _run_step([sys.executable, str(ROOT / "scripts" / "hermes_supabase_strategy_search.py"), "--asset-class", args.asset_class if args.asset_class != "all" else "forex", "--limit", "20"]),
        "tournament_dry_run": _run_step([sys.executable, str(ROOT / "scripts" / "run_nexus_trading_tournament.py"), "--mode", "paper", "--source", "supabase_first", "--data-source", "oanda_practice", "--dry-run"]),
    }

    payload = {
        "generated_at": _now(),
        "source_mode": args.source,
        "asset_class": args.asset_class,
        "dry_run": args.dry_run,
        "registry_sources_configured": len([row for row in registry_rows if row.get("enabled") and str(row.get("source_type", "")).startswith("youtube")]),
        "channels_found": configured_channels,
        "keyword_searches_configured": configured_searches,
        "urls_supported": True,
        "transcripts_supported": True,
        "documents_reviewed": len(docs),
        "videos_transcripts_reviewed": [doc.source_title for doc in docs[:25]],
        "strategies_extracted": len(deduped),
        "testable_strategies": len(testable),
        "needs_research_strategies": len(needs_research),
        "seeds_found": len(deduped_seeds),
        "seed_types": sorted({seed.get("seed_type") for seed in deduped_seeds if seed.get("seed_type")}),
        "duplicates_skipped": duplicates_skipped,
        "rows_written": rows_written,
        "rows_inserted": rows_inserted,
        "table_used": table_used,
        "candidates_searchable": handoff_steps["supabase_strategy_search"]["ok"],
        "result_interpretation": result_interpretation,
        "next_safe_action": next_safe_action,
        "requires_ray_approval": False,
        "handoff": handoff_steps,
        "strategies": deduped,
        "seeds": deduped_seeds,
    }
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2, default=str))
    lines = [
        "# YouTube Strategy Research",
        "",
        f"- Generated at: `{payload['generated_at']}`",
        f"- Source mode: `{args.source}`",
        f"- Asset class: `{args.asset_class}`",
        f"- Dry run: `{'yes' if args.dry_run else 'no'}`",
        f"- Registry sources configured: `{payload['registry_sources_configured']}`",
        f"- Channels found: `{configured_channels}`",
        f"- Keyword searches configured: `{configured_searches}`",
        f"- URLs supported: `yes`",
        f"- Transcripts supported: `yes`",
        f"- Videos/transcripts reviewed: `{len(docs)}`",
        f"- Strategies extracted: `{len(deduped)}`",
        f"- Testable strategies: `{len(testable)}`",
        f"- Needs research: `{len(needs_research)}`",
        f"- Seeds found: `{len(deduped_seeds)}`",
        f"- Duplicates skipped: `{duplicates_skipped}`",
        f"- Supabase table used: `{table_used}`",
        f"- Rows written: `{'yes' if rows_written else 'no'}`",
        f"- Result interpretation: `{result_interpretation}`",
        f"- Next safe action: `{next_safe_action}`",
        "",
        "## Reviewed Sources",
    ]
    for doc in docs[:15]:
        lines.append(f"- `{doc.source_title}` source=`{doc.source_type}` channel=`{doc.source_channel or 'unknown'}`")
    lines.append("")
    lines.append("## Extracted Strategies")
    for row in deduped[:20]:
        lines.append(
            f"- `{row['strategy_id']}` family=`{row['strategy_family']}` trigger=`{row['trigger_type']}` "
            f"status=`{row['status']}` symbol=`{','.join(row['symbols'])}` source=`{row['source_title']}`"
        )
    lines.append("")
    lines.append("## Seeds")
    for seed in deduped_seeds[:20]:
        lines.append(
            f"- `{seed['seed_id']}` type=`{seed['seed_type']}` family=`{seed['strategy_family']}` "
            f"symbol=`{','.join(seed['symbols'])}` missing=`{', '.join(seed['missing_fields']) or 'none'}`"
        )
    OUTPUT_MD.write_text("\n".join(lines) + "\n")

    discover_cmd = [
        sys.executable,
        str(ROOT / "scripts" / "discover_trading_strategies.py"),
        "--asset-class",
        args.asset_class if args.asset_class != "all" else "forex",
        "--source",
        "all",
        "--dry-run",
    ]
    _run_step(discover_cmd)

    print(json.dumps({"json": str(OUTPUT_JSON), "markdown": str(OUTPUT_MD), "summary": payload}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
