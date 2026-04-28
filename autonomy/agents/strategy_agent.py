"""
Strategy Agent.

Handles high_ranked_strategy events emitted by the research pipeline.
Converts strategy text into a concrete trading signal and submits it to
the trading engine /signal/manual endpoint for paper testing.

Subscriptions:
  high_ranked_strategy — strategy scored >= threshold by strategy_ranker
"""

import os
import re
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

from autonomy.agents.base_agent      import BaseAgent
from autonomy.output_service         import log_action
from autonomy.nexus_super_prompt     import build_nexus_prompt

TRADING_ENGINE_URL = os.getenv("TRADING_ENGINE_URL", "http://127.0.0.1:5000")
OPENROUTER_KEY     = os.getenv("OPENROUTER_API_KEY", "")
GROQ_KEY           = os.getenv("GROQ_API_KEY", "")
SUPABASE_URL       = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY       = os.getenv("SUPABASE_KEY", "")

_EXTRACT_PROMPT = """\
You are a forex trading assistant. Given a strategy description, extract the trading signal direction.
Return JSON only — no prose.

Return exactly:
{
  "action": "BUY" or "SELL",
  "confidence": 50-95,
  "reasoning": "one sentence"
}

Rules:
- "BUY" if the strategy looks for upward price movement, bullish patterns, or long entries.
- "SELL" if the strategy looks for downward movement, bearish patterns, or short entries.
- When ambiguous, return "BUY"."""


def _extract_action(strategy_text: str) -> dict:
    """Call LLM to determine BUY/SELL direction. Falls back to BUY on error."""
    providers = []
    if OPENROUTER_KEY:
        providers.append({
            "url": "https://openrouter.ai/api/v1/chat/completions",
            "key": OPENROUTER_KEY,
            "model": "meta-llama/llama-3.3-70b-instruct",
        })
    if GROQ_KEY:
        providers.append({
            "url": "https://api.groq.com/openai/v1/chat/completions",
            "key": GROQ_KEY,
            "model": "llama-3.3-70b-versatile",
        })

    logger = logging.getLogger("StrategyAgent")
    for p in providers:
        try:
            body = json.dumps({
                "model": p["model"],
                "messages": [
                    {"role": "system", "content": _EXTRACT_PROMPT},
                    {"role": "user",   "content": f"Strategy:\n{strategy_text[:1500]}"},
                ],
                "max_tokens": 120,
                "temperature": 0.1,
            }).encode()
            req = urllib.request.Request(
                p["url"], data=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {p['key']}",
                },
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            raw = data["choices"][0]["message"]["content"]
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if m:
                return json.loads(m.group())
        except Exception as e:
            logger.warning(f"LLM extract error ({p['url']}): {e}")
            continue
    return {"action": "BUY", "confidence": 60, "reasoning": "LLM unavailable — defaulting to BUY"}


def _extract_action_with_prompt(strategy_text: str, system_prompt: str) -> dict:
    """Same as _extract_action but uses a custom system prompt (e.g. Nexus Super Prompt)."""
    providers = []
    if OPENROUTER_KEY:
        providers.append({
            "url": "https://openrouter.ai/api/v1/chat/completions",
            "key": OPENROUTER_KEY,
            "model": "meta-llama/llama-3.3-70b-instruct",
        })
    if GROQ_KEY:
        providers.append({
            "url": "https://api.groq.com/openai/v1/chat/completions",
            "key": GROQ_KEY,
            "model": "llama-3.3-70b-versatile",
        })

    logger = logging.getLogger("StrategyAgent")
    for p in providers:
        try:
            body = json.dumps({
                "model": p["model"],
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": f"Strategy:\n{strategy_text[:1500]}\n\nReturn JSON with action (BUY/SELL), confidence (50-95), and reasoning."},
                ],
                "max_tokens": 200,
                "temperature": 0.2,
            }).encode()
            req = urllib.request.Request(
                p["url"], data=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {p['key']}",
                },
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            raw = data["choices"][0]["message"]["content"]
            m = re.search(r"\{.*?\}", raw, re.DOTALL)
            if m:
                result = json.loads(m.group())
                if "action" in result:
                    return result
        except Exception as e:
            logger.warning(f"LLM nexus-prompt extract error ({p['url']}): {e}")
            continue
    return _extract_action(strategy_text)


def _post_manual_signal(signal: dict) -> dict:
    """POST signal to trading engine /signal/manual."""
    body = json.dumps(signal).encode()
    req  = urllib.request.Request(
        f"{TRADING_ENGINE_URL}/signal/manual",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode()[:200]}"}
    except Exception as e:
        return {"error": str(e)}


def _sb_patch(path: str, body: dict) -> bool:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False
    try:
        data = json.dumps(body).encode()
        req  = urllib.request.Request(
            f"{SUPABASE_URL}/rest/v1/{path}",
            data=data,
            headers={
                "apikey":        SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type":  "application/json",
                "Prefer":        "return=minimal",
            },
            method="PATCH",
        )
        with urllib.request.urlopen(req, timeout=10) as _:
            return True
    except Exception as e:
        logging.getLogger("StrategyAgent").warning(f"Supabase PATCH {path}: {e}")
        return False


class StrategyAgent(BaseAgent):
    NAME             = "strategy_agent"
    COOLDOWN_MINUTES = 0   # No client cooldown — strategies are unique
    SUBSCRIPTIONS    = ["high_ranked_strategy"]

    def _act(self, event: dict, context: dict) -> list:
        payload     = event.get("payload") or {}
        event_id    = event.get("id")
        strategy_id = payload.get("strategy_id")
        rank_score  = float(payload.get("rank_score", 0))
        summary     = payload.get("summary", "")
        instruments = payload.get("instruments") or ["EURUSD"]
        timeframes  = payload.get("timeframes")  or ["H1"]
        strat_text  = payload.get("strategy_text") or summary
        outputs     = []

        symbol    = instruments[0] if instruments else "EURUSD"
        timeframe = timeframes[0]  if timeframes  else "H1"

        if payload.get("use_nexus_super_prompt"):
            nexus_prompt = build_nexus_prompt(
                role_name="funding_strategist",
                task_description=strat_text[:800],
                user_stage="building",
                current_goal="Evaluate and paper-test this trading strategy",
                user_data=f"rank_score={rank_score}, instruments={instruments}, timeframes={timeframes}",
            )
            extracted = _extract_action_with_prompt(strat_text, nexus_prompt)
        else:
            extracted  = _extract_action(strat_text)
        action     = extracted.get("action", "BUY").upper()
        confidence = int(extracted.get("confidence", round(rank_score * 10)))

        signal = {
            "symbol":      symbol,
            "action":      action,
            "timeframe":   timeframe,
            "strategy":    "strategy_research",
            "confidence":  confidence,
            "strategy_id": strategy_id,
            "rank_score":  rank_score,
        }

        result = _post_manual_signal(signal)
        self.logger.info(f"Paper signal: {symbol} {action} tf={timeframe} → {result}")

        if strategy_id and "error" not in result:
            _sb_patch(
                f"ranked_strategies?id=eq.{strategy_id}",
                {
                    "event_emitted": True,
                    "paper_tested":  True,
                    "updated_at":    datetime.now(timezone.utc).isoformat(),
                },
            )

        log_action(
            self.NAME,
            "paper_signal_submitted",
            None,        # no client
            event_id,
            "high_ranked_strategy",
            strategy_id,
            f"rank={rank_score}, {symbol} {action} {timeframe}, result={json.dumps(result)[:120]}",
        )

        outputs.append({
            "type":        "signal",
            "symbol":      symbol,
            "action":      action,
            "timeframe":   timeframe,
            "result":      result,
            "strategy_id": strategy_id,
        })
        return outputs
