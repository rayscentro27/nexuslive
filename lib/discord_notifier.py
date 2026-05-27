"""
discord_notifier.py — Nexus Discord Webhook Integration

Three channels:
  CEO Command    — executive briefings, KPIs, revenue progress, priority actions
  Content Engine — YouTube scripts, newsletters, SEO articles, hooks, CTA drafts
  System Ops     — PM2 crashes, watcher failures, OpenRouter errors, degraded systems

Usage:
    from lib.discord_notifier import ceo, content, ops

    ceo.send_briefing(briefing_markdown)
    content.send_draft("youtube_script", title, body, topic)
    ops.alert("critical", "Watcher loop stalled", detail="no findings in 4h")

Discord limits (enforced here):
  embed title:       256 chars
  embed description: 4096 chars
  field value:       1024 chars
  total per embed:   6000 chars
  rate limit:        30 req/min per webhook
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

# ── Webhook URLs ──────────────────────────────────────────────────────────────
_CEO_URL     = os.getenv("DISCORD_CEO_WEBHOOK", "").strip()
_CONTENT_URL = os.getenv("DISCORD_CONTENT_WEBHOOK", "").strip()
_OPS_URL     = os.getenv("DISCORD_OPS_WEBHOOK", "").strip()

# ── Embed colors ──────────────────────────────────────────────────────────────
COLOR_CEO         = 0x7C3AED   # purple — executive
COLOR_REVENUE     = 0xF97316   # orange — monetization
COLOR_CONTENT     = 0x10B981   # emerald — creative output
COLOR_OPS_OK      = 0x3B82F6   # blue — healthy
COLOR_OPS_WARN    = 0xF59E0B   # amber — warning
COLOR_OPS_CRIT    = 0xEF4444   # red — critical
COLOR_OPS_DEGRADE = 0x6B7280   # gray — degraded

# ── Rate limit state (per URL) ────────────────────────────────────────────────
_LAST_SEND: dict[str, float] = {}
_MIN_INTERVAL = 2.0  # minimum seconds between sends to same webhook


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _trunc(text: str, limit: int) -> str:
    text = str(text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _send_raw(url: str, payload: dict) -> bool:
    """POST payload to Discord webhook. Returns True on success."""
    if not url:
        return False

    # Basic rate limiting
    last = _LAST_SEND.get(url, 0)
    wait = _MIN_INTERVAL - (time.time() - last)
    if wait > 0:
        time.sleep(wait)

    data = json.dumps(payload, default=str).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json", "User-Agent": "NexusAI/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            _LAST_SEND[url] = time.time()
            return resp.status in (200, 204)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:200]
        print(f"[discord] HTTP {e.code} → {url[:60]}: {body}")
        return False
    except Exception as exc:
        print(f"[discord] send error: {exc}")
        return False


def send_message(url: str, content: str) -> bool:
    """Send a plain text message."""
    return _send_raw(url, {"content": _trunc(content, 2000)})


def send_embed(
    url: str,
    title: str,
    description: str = "",
    color: int = COLOR_OPS_OK,
    fields: Optional[list[dict]] = None,
    footer: str = "Nexus AI Wealth",
    username: str = "Nexus",
) -> bool:
    """Send a rich embed."""
    embed: dict = {
        "title": _trunc(title, 256),
        "color": color,
        "timestamp": _now_iso(),
        "footer": {"text": footer},
    }
    if description:
        embed["description"] = _trunc(description, 4096)
    if fields:
        cleaned = []
        for f in fields[:25]:
            cleaned.append({
                "name": _trunc(f.get("name", ""), 256),
                "value": _trunc(f.get("value", "​"), 1024),
                "inline": bool(f.get("inline", False)),
            })
        embed["fields"] = cleaned

    return _send_raw(url, {"username": username, "embeds": [embed]})


# ── CEO Channel ───────────────────────────────────────────────────────────────

class CEONotifier:
    """Posts executive-level intelligence to the CEO Command channel."""

    def send_briefing(self, briefing_markdown: str) -> bool:
        """Post the full morning briefing, split into readable sections."""
        if not _CEO_URL:
            return False
        lines = briefing_markdown.strip().splitlines()

        # Extract title line
        title = next((l.lstrip("#").strip() for l in lines if l.startswith("#")), "NEXUS BRIEFING")

        # Extract sections (## headers)
        sections: list[tuple[str, str]] = []
        current_header = ""
        current_body: list[str] = []
        for line in lines:
            if line.startswith("## "):
                if current_header:
                    sections.append((current_header, "\n".join(current_body).strip()))
                current_header = line.lstrip("#").strip()
                current_body = []
            elif not line.startswith("# "):
                current_body.append(line)
        if current_header:
            sections.append((current_header, "\n".join(current_body).strip()))

        # Build fields from first 8 sections (Discord embed field limit)
        fields = []
        for header, body in sections[:8]:
            if body:
                fields.append({"name": header, "value": _trunc(body, 1024), "inline": False})

        ok = send_embed(
            _CEO_URL,
            title=_trunc(title, 256),
            description="**Daily operational intelligence. High-signal only.**",
            color=COLOR_CEO,
            fields=fields,
            footer="Nexus CEO Command",
            username="Hermes",
        )

        # Post remaining sections as follow-up if needed
        if len(sections) > 8:
            remainder = "\n\n".join(
                f"**{h}**\n{b}" for h, b in sections[8:12] if b
            )
            if remainder:
                time.sleep(_MIN_INTERVAL)
                send_embed(
                    _CEO_URL,
                    title="Briefing (cont.)",
                    description=_trunc(remainder, 4096),
                    color=COLOR_CEO,
                    footer="Nexus CEO Command",
                    username="Hermes",
                )
        return ok

    def send_opportunity(self, title: str, summary: str, roi_score: float,
                         priority: str = "HIGH") -> bool:
        color = COLOR_REVENUE if priority.upper() == "CRITICAL" else COLOR_CEO
        return send_embed(
            _CEO_URL,
            title=f"💰 Opportunity: {_trunc(title, 200)}",
            description=_trunc(summary, 1024),
            color=color,
            fields=[
                {"name": "Priority", "value": priority.upper(), "inline": True},
                {"name": "ROI Score", "value": str(roi_score), "inline": True},
            ],
            footer="Nexus Monetization Intelligence",
            username="Hermes",
        )

    def send_kpi_update(self, metrics: dict) -> bool:
        fields = [
            {"name": k.replace("_", " ").title(), "value": str(v), "inline": True}
            for k, v in list(metrics.items())[:12]
        ]
        return send_embed(
            _CEO_URL,
            title="📊 KPI Update",
            color=COLOR_REVENUE,
            fields=fields,
            footer="Nexus Revenue Tracking",
            username="Hermes",
        )

    def send_priority_actions(self, actions: list[str]) -> bool:
        body = "\n".join(f"• {a}" for a in actions[:10])
        return send_embed(
            _CEO_URL,
            title="⚡ Priority Actions",
            description=_trunc(body, 2048),
            color=COLOR_CEO,
            footer="Nexus CEO Command",
            username="Hermes",
        )


# ── Content Channel ───────────────────────────────────────────────────────────

# Content type display config
_CONTENT_META: dict[str, dict] = {
    "youtube_script": {"emoji": "🎬", "label": "YouTube Script"},
    "newsletter":     {"emoji": "📧", "label": "Newsletter Draft"},
    "seo_article":    {"emoji": "📝", "label": "SEO Article"},
    "linkedin_post":  {"emoji": "💼", "label": "LinkedIn Post"},
    "tiktok_hook":    {"emoji": "🎵", "label": "TikTok Hook"},
    "x_post":         {"emoji": "🐦", "label": "X Post"},
    "affiliate":      {"emoji": "🔗", "label": "Affiliate Content"},
    "cta":            {"emoji": "🎯", "label": "CTA Copy"},
    "landing_page":   {"emoji": "🏠", "label": "Landing Page"},
}


class ContentNotifier:
    """Posts content drafts to the Content Engine channel."""

    def send_draft(self, content_type: str, title: str, body: str,
                   topic: str = "", word_count: int = 0,
                   quality_score: int = 0, row_id: str = "") -> bool:
        if not _CONTENT_URL:
            return False
        meta = _CONTENT_META.get(content_type, {"emoji": "📄", "label": content_type.replace("_", " ").title()})
        emoji, label = meta["emoji"], meta["label"]

        # For long content, show preview + key section
        preview = _trunc(body, 800)

        fields = []
        if topic:
            fields.append({"name": "Topic", "value": topic, "inline": True})
        if word_count:
            fields.append({"name": "Words", "value": str(word_count), "inline": True})
        if quality_score:
            fields.append({"name": "Quality", "value": f"{quality_score}/100", "inline": True})
        if row_id:
            fields.append({"name": "Evidence", "value": f"`{row_id[:16]}...`", "inline": True})
        fields.append({"name": "Status", "value": "📋 Draft — Awaiting Approval", "inline": True})

        return send_embed(
            _CONTENT_URL,
            title=f"{emoji} {label}: {_trunc(title, 180)}",
            description=f"```\n{preview}\n```",
            color=COLOR_CONTENT,
            fields=fields,
            footer="Nexus Content Engine",
            username="Content Worker",
        )

    def send_pipeline_summary(self, date: str, topic: str,
                              outputs: list[dict], errors: list[dict]) -> bool:
        if not _CONTENT_URL:
            return False
        fields = []
        for o in outputs[:10]:
            ct = o.get("type", "?")
            meta = _CONTENT_META.get(ct, {"emoji": "📄", "label": ct})
            words = o.get("words", "")
            rid = o.get("row_id", "")
            val = f"{meta['emoji']} {meta['label']}"
            if words:
                val += f" | {words}w"
            if rid:
                val += f" | `{str(rid)[:8]}…`"
            fields.append({"name": ct.replace("_", " ").title(), "value": val, "inline": True})

        if errors:
            fields.append({"name": "⚠️ Errors", "value": "\n".join(e.get("label","?") for e in errors[:5]), "inline": False})

        return send_embed(
            _CONTENT_URL,
            title=f"📦 Content Pipeline Complete — {date}",
            description=f"**Topic:** {topic}\n**Outputs:** {len(outputs)} | **Errors:** {len(errors)}",
            color=COLOR_CONTENT if not errors else COLOR_OPS_WARN,
            fields=fields,
            footer="Nexus Content Engine",
            username="Content Worker",
        )


# ── System Ops Channel ────────────────────────────────────────────────────────

_ALERT_COLORS = {
    "critical": COLOR_OPS_CRIT,
    "warning":  COLOR_OPS_WARN,
    "info":     COLOR_OPS_OK,
    "degraded": COLOR_OPS_DEGRADE,
}

_ALERT_EMOJI = {
    "critical": "🚨",
    "warning":  "⚠️",
    "info":     "ℹ️",
    "degraded": "🔻",
}


class OpsNotifier:
    """Posts system alerts and operational status to the System Ops channel."""

    def alert(self, level: str, title: str, detail: str = "",
              fields: Optional[list[dict]] = None) -> bool:
        if not _OPS_URL:
            return False
        level = level.lower()
        emoji = _ALERT_EMOJI.get(level, "🔔")
        color = _ALERT_COLORS.get(level, COLOR_OPS_OK)
        return send_embed(
            _OPS_URL,
            title=f"{emoji} {_trunc(title, 230)}",
            description=_trunc(detail, 2048) if detail else "",
            color=color,
            fields=fields or [],
            footer="Nexus System Ops",
            username="Ops Monitor",
        )

    def send_pm2_status(self, processes: list[dict]) -> bool:
        if not _OPS_URL:
            return False
        fields = []
        has_problem = False
        for p in processes:
            name = p.get("name", "?")
            status = p.get("status", "?")
            restarts = p.get("restarts", 0)
            mem = p.get("memory", "")
            emoji = "✅" if status == "online" else "❌"
            if status != "online" or restarts > 3:
                has_problem = True
            val = f"{emoji} {status}"
            if mem:
                val += f" | {mem}"
            if restarts:
                val += f" | ↺{restarts}"
            fields.append({"name": name, "value": val, "inline": True})

        color = COLOR_OPS_CRIT if has_problem else COLOR_OPS_OK
        return send_embed(
            _OPS_URL,
            title="🖥️ PM2 Runtime Status",
            color=color,
            fields=fields,
            footer="Nexus System Ops",
            username="Ops Monitor",
        )

    def send_watcher_summary(self, summary: dict) -> bool:
        if not _OPS_URL:
            return False
        ran = summary.get("watchers_ran", [])
        findings = summary.get("total_findings", 0)
        fields = [
            {"name": "Active Watchers", "value": ", ".join(ran) or "none", "inline": False},
            {"name": "Total Findings", "value": str(findings), "inline": True},
        ]
        if summary.get("consensus_top"):
            fields.append({"name": "Top Opportunity", "value": summary["consensus_top"], "inline": False})
        color = COLOR_OPS_OK if ran else COLOR_OPS_WARN
        return send_embed(
            _OPS_URL,
            title="👁️ Watcher Cycle Complete",
            color=color,
            fields=fields,
            footer="Nexus Intelligence Watchers",
            username="Ops Monitor",
        )

    def send_openrouter_health(self, healthy: bool, model: str = "",
                               latency: float = 0, error: str = "") -> bool:
        if not _OPS_URL:
            return False
        fields = []
        if model:
            fields.append({"name": "Model", "value": model, "inline": True})
        if latency:
            fields.append({"name": "Latency", "value": f"{latency:.2f}s", "inline": True})
        if error:
            fields.append({"name": "Error", "value": _trunc(error, 500), "inline": False})
        level = "info" if healthy else "critical"
        status = "✅ Healthy" if healthy else "❌ FAILED"
        return self.alert(
            level,
            f"OpenRouter {status}",
            fields=fields,
        )


# ── Singleton instances ───────────────────────────────────────────────────────

ceo     = CEONotifier()
content = ContentNotifier()
ops     = OpsNotifier()


# ── Convenience helpers ───────────────────────────────────────────────────────

def configured_channels() -> dict[str, bool]:
    return {
        "ceo":     bool(_CEO_URL),
        "content": bool(_CONTENT_URL),
        "ops":     bool(_OPS_URL),
    }


def verify_webhooks() -> dict[str, bool]:
    """Send a minimal test ping to each configured webhook. Returns success map."""
    results: dict[str, bool] = {}
    for name, url in [("ceo", _CEO_URL), ("content", _CONTENT_URL), ("ops", _OPS_URL)]:
        if not url:
            results[name] = False
            continue
        ok = _send_raw(url, {
            "username": "Nexus",
            "content": f"✅ Nexus webhook verified — {name.upper()} channel connected.",
        })
        results[name] = ok
        time.sleep(_MIN_INTERVAL)
    return results
