"""
Transcript summary -> research_artifacts publisher.

Reads local `.summary` files from `research-engine/summaries`, infers a topic,
extracts lightweight structured fields, and writes rows into
`public.research_artifacts`.
"""

from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
SUMMARY_DIR = ROOT / "research-engine" / "summaries"

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")


def _headers(prefer: str = "return=representation") -> Dict[str, str]:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }


def _sb_get(path: str) -> List[dict]:
    req = urllib.request.Request(f"{SUPABASE_URL}/rest/v1/{path}", headers=_headers())
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.loads(response.read())


def _sb_insert(table: str, row: dict) -> Optional[dict]:
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/{table}",
        data=json.dumps(row).encode(),
        headers=_headers(),
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        rows = json.loads(response.read())
        return rows[0] if rows else None


def _slug_title(name: str) -> str:
    return Path(name).stem.replace(".en.vtt", "").replace(".summary", "")


def _infer_topic(title: str, content: str) -> str:
    text = f"{title}\n{content}".lower()
    if any(k in text for k in ("crm", "go high level", "sales pipeline", "lead nurture", "appointment setter", "automation agency")):
        return "crm_automation"
    if any(k in text for k in ("grant", "sba", "grant funding", "business credit", "credit repair")):
        return "general_business_intelligence"
    if any(k in text for k in ("saas", "agency", "offer", "acquisition", "service business", "local business", "online business", "lead generation", "client acquisition", "recurring revenue")):
        return "business_opportunities"
    return "trading"


def _infer_subtheme(title: str, content: str, topic: str) -> str:
    text = f"{title}\n{content}".lower()
    if topic == "trading":
        if "options" in text:
            return "options"
        if any(k in text for k in ("crypto", "bitcoin", "eth", "defi")):
            return "crypto"
        if any(k in text for k in ("forex", "eurusd", "gbpusd", "xauusd", "gold")):
            return "forex"
        return "market_analysis"
    if topic == "crm_automation":
        return "crm_automation"
    if topic == "business_opportunities":
        if "agency" in text:
            return "agency"
        if "saas" in text:
            return "saas"
        if "ecommerce" in text:
            return "ecommerce"
        if "local business" in text:
            return "local_business"
        return "business_model"
    return "general_business"


def _split_sections(content: str) -> Dict[str, str]:
    current = "summary"
    sections: Dict[str, List[str]] = {current: []}
    for raw_line in content.splitlines():
        line = raw_line.strip()
        header = re.match(r"^\*{0,2}([A-Za-z][A-Za-z /:-]{2,50})\*{0,2}:\s*$", line)
        if header:
            current = header.group(1).strip().lower().replace(" ", "_")
            sections.setdefault(current, [])
            continue
        if line:
            sections.setdefault(current, []).append(line)
    return {key: "\n".join(value).strip() for key, value in sections.items() if value}


def _clean_text(text: str) -> str:
    value = str(text or "")
    value = re.sub(r"Kind:\s*captions\s*Language:\s*[a-z-]+\s*", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _is_noise_text(text: str) -> bool:
    lower = _clean_text(text).lower()
    if not lower:
        return True
    noise_markers = [
        "you have hit your chatgpt usage limit",
        "try again in",
        "usage limit",
        "kind: captions language:",
    ]
    return any(marker in lower for marker in noise_markers)


def _bulletish(text: str, limit: int = 5) -> List[str]:
    items: List[str] = []
    for line in text.splitlines():
        cleaned = _clean_text(line.strip().lstrip("-*•").strip())
        if _is_noise_text(cleaned):
            continue
        if cleaned:
            items.append(cleaned[:240])
        if len(items) >= limit:
            break
    if items:
        return items
    sentences = [
        _clean_text(s.strip())
        for s in re.split(r"[.!?]\s+", text)
        if len(_clean_text(s.strip())) > 20 and not _is_noise_text(s)
    ]
    return [s[:240] for s in sentences[:limit]]


def _build_row(path: Path) -> dict:
    content = path.read_text(encoding="utf-8", errors="ignore")
    title = _slug_title(path.name)
    topic = _infer_topic(title, content)
    subtheme = _infer_subtheme(title, content, topic)
    sections = _split_sections(content)
    summary = _clean_text(sections.get("summary", content[:1000]))

    key_points = _bulletish(
        "\n".join(filter(None, [
            sections.get("strategies", ""),
            sections.get("indicators", ""),
            sections.get("trade_setups", ""),
            sections.get("summary", ""),
        ]))
    )
    action_items = _bulletish(
        "\n".join(filter(None, [
            sections.get("strategies", ""),
            sections.get("psychology", ""),
        ])),
        limit=4,
    )
    risk_warnings = _bulletish(
        "\n".join(filter(None, [
            sections.get("risk_management", ""),
            sections.get("psychology", ""),
        ])),
        limit=4,
    )
    opportunity_notes = _bulletish(
        "\n".join(filter(None, [
            sections.get("summary", ""),
            sections.get("strategies", ""),
        ])),
        limit=4,
    )

    return {
        "source": "research-engine",
        "source_type": "youtube_channel",
        "source_url": None,
        "topic": topic,
        "subtheme": subtheme,
        "subthemes": [subtheme],
        "title": title,
        "summary": summary,
        "content": content,
        "key_points": key_points,
        "action_items": action_items,
        "risk_warnings": risk_warnings,
        "opportunity_notes": opportunity_notes,
        "published_at": None,
        "trace_id": None,
    }


def _already_exists(title: str, topic: str) -> bool:
    encoded_title = urllib.parse.quote(title, safe="")
    rows = _sb_get(
        f"research_artifacts?title=eq.{encoded_title}&topic=eq.{topic}&select=id&limit=1"
    )
    return bool(rows)


def publish(limit: int = 25) -> dict:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")

    files = sorted(SUMMARY_DIR.glob("*.summary"), key=lambda p: p.stat().st_mtime, reverse=True)
    inserted = 0
    skipped = 0
    topics: Dict[str, int] = {}

    for path in files[:limit]:
        row = _build_row(path)
        if _is_noise_text(row.get("summary")):
            skipped += 1
            continue
        if _already_exists(row["title"], row["topic"]):
            skipped += 1
            continue
        _sb_insert("research_artifacts", row)
        inserted += 1
        topics[row["topic"]] = topics.get(row["topic"], 0) + 1

    return {"inserted": inserted, "skipped": skipped, "topics": topics}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args()
    print(json.dumps(publish(limit=args.limit), indent=2))
