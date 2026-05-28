"""
Premium Blocker Resolver
Researches free/cheaper alternatives when a paid tool (e.g. Beehiiv) blocks progress.
Saves resolution packets to docs/reports/premium_blockers/.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

BLOCKERS_DIR = Path("docs/reports/premium_blockers")
BLOCKERS_DIR.mkdir(parents=True, exist_ok=True)

# Known blocker alternatives (curated, kept up-to-date with real options)
KNOWN_ALTERNATIVES: dict[str, list[dict]] = {
    "beehiiv": [
        {
            "name": "Substack",
            "url": "https://substack.com",
            "free_tier": True,
            "monetization": "paid subscriptions built-in",
            "api": False,
            "notes": "No code/embed customization. Large built-in audience discovery.",
        },
        {
            "name": "Ghost (self-hosted)",
            "url": "https://ghost.org/docs/install/",
            "free_tier": True,
            "monetization": "Stripe integration, memberships",
            "api": True,
            "notes": "Free to self-host on Oracle ARM instance. Full API. Best Beehiiv alternative for tech users.",
        },
        {
            "name": "ConvertKit Free",
            "url": "https://convertkit.com",
            "free_tier": True,
            "monetization": "paid subscriptions, commerce",
            "api": True,
            "notes": "Free up to 1,000 subscribers. Strong automation. Rebranded to Kit.",
        },
        {
            "name": "MailerLite",
            "url": "https://www.mailerlite.com",
            "free_tier": True,
            "monetization": "paid newsletters, landing pages",
            "api": True,
            "notes": "Free up to 1,000 subscribers / 12,000 emails/month. Good for beginners.",
        },
        {
            "name": "Buttondown",
            "url": "https://buttondown.email",
            "free_tier": True,
            "monetization": "paid subscriptions",
            "api": True,
            "notes": "Dev-friendly, Markdown native. Free up to 100 subscribers.",
        },
    ],
    "convertkit": [
        {
            "name": "MailerLite",
            "url": "https://www.mailerlite.com",
            "free_tier": True,
            "monetization": "paid newsletters",
            "api": True,
            "notes": "More generous free tier than ConvertKit.",
        },
        {
            "name": "Brevo (SendinBlue)",
            "url": "https://www.brevo.com",
            "free_tier": True,
            "monetization": "email campaigns, transactional",
            "api": True,
            "notes": "300 emails/day free. Strong API. Good for automation.",
        },
    ],
    "discord_webhooks": [
        {
            "name": "Telegram Bot API",
            "url": "https://core.telegram.org/bots/api",
            "free_tier": True,
            "monetization": "N/A",
            "api": True,
            "notes": "Already integrated in Nexus via Hermes. Zero cost.",
        },
        {
            "name": "Slack Webhook (free workspace)",
            "url": "https://api.slack.com/messaging/webhooks",
            "free_tier": True,
            "monetization": "N/A",
            "api": True,
            "notes": "Free workspace webhook. 90-day message history limit.",
        },
    ],
    "openai": [
        {
            "name": "OpenRouter (deepseek-chat)",
            "url": "https://openrouter.ai",
            "free_tier": False,
            "monetization": "N/A",
            "api": True,
            "notes": "Already integrated. Cheapest capable model via OpenRouter.",
        },
        {
            "name": "Ollama (local)",
            "url": "https://ollama.com",
            "free_tier": True,
            "monetization": "N/A",
            "api": True,
            "notes": "Free local LLM. Currently offline — verify port 11434 on Oracle VM.",
        },
        {
            "name": "Groq (free tier)",
            "url": "https://console.groq.com",
            "free_tier": True,
            "monetization": "N/A",
            "api": True,
            "notes": "Fast inference. Free tier: 14,400 tokens/min. Llama-3.3-70B.",
        },
    ],
}


class PremiumBlockerResolver:
    """
    Given a blocked tool name, research and return the best free/cheaper alternative.
    """

    def resolve(self, blocked_tool: str, context: str = "") -> dict[str, Any]:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        tool_key = blocked_tool.lower().strip()

        alternatives = KNOWN_ALTERNATIVES.get(tool_key, [])
        if not alternatives:
            # Generic fallback
            resolution = self._generic_resolution(blocked_tool)
        else:
            resolution = self._rank_alternatives(blocked_tool, alternatives, context)

        packet = {
            "run_id": f"blocker_{ts}",
            "blocked_tool": blocked_tool,
            "context": context,
            "alternatives_count": len(alternatives),
            "top_recommendation": resolution.get("top_pick"),
            "full_alternatives": alternatives,
            "resolution_notes": resolution.get("notes", ""),
            "resolved_at": datetime.utcnow().isoformat() + "Z",
        }

        md_path = self._save_report(packet, ts)
        packet["report_path"] = str(md_path)
        return packet

    def all_known_blockers(self) -> list[str]:
        return list(KNOWN_ALTERNATIVES.keys())

    # ── internals ──────────────────────────────────────────────────────────────

    def _rank_alternatives(self, tool: str, alternatives: list[dict], context: str) -> dict:
        # Prefer free-tier + API-capable
        scored = []
        for alt in alternatives:
            score = 0
            if alt.get("free_tier"):
                score += 3
            if alt.get("api"):
                score += 2
            scored.append((score, alt))
        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[0][1] if scored else alternatives[0]
        return {
            "top_pick": top,
            "notes": f"Best free/API-capable replacement for {tool}: {top['name']}. {top['notes']}",
        }

    def _generic_resolution(self, tool: str) -> dict:
        return {
            "top_pick": None,
            "notes": (
                f"No curated alternatives for '{tool}'. "
                "Research free-tier SaaS directories (alternativeto.net) "
                "or open-source GitHub repos before purchasing."
            ),
        }

    def _save_report(self, packet: dict, ts: str) -> Path:
        tool = packet["blocked_tool"].replace(" ", "_").lower()
        md_lines = [
            f"# Premium Blocker Resolution — {packet['blocked_tool']}",
            f"*Run: {ts} | Context: {packet['context'] or 'N/A'}*\n",
            f"## Top Recommendation",
        ]
        top = packet.get("top_recommendation")
        if top:
            md_lines += [
                f"**{top['name']}** — {top.get('url', '')}",
                f"- Free tier: {top['free_tier']}",
                f"- API: {top['api']}",
                f"- Monetization: {top.get('monetization', 'N/A')}",
                f"- Notes: {top.get('notes', '')}",
                "",
            ]
        else:
            md_lines.append("No curated recommendation available.\n")

        md_lines.append("## All Alternatives")
        for alt in packet["full_alternatives"]:
            md_lines.append(f"### {alt['name']}")
            md_lines += [
                f"- URL: {alt.get('url', '')}",
                f"- Free tier: {alt['free_tier']} | API: {alt['api']}",
                f"- Notes: {alt.get('notes', '')}",
                "",
            ]
        md_lines.append(f"\n*Resolution notes: {packet['resolution_notes']}*")

        path = BLOCKERS_DIR / f"blocker_resolution_{tool}_{ts}.md"
        path.write_text("\n".join(md_lines))

        json_path = BLOCKERS_DIR / f"blocker_resolution_{tool}_{ts}.json"
        json_path.write_text(json.dumps(packet, indent=2, default=str))
        return path
