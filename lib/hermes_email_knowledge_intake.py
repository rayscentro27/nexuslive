from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import hashlib
import json
import os
import re
from html import unescape


ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT / "reports" / "knowledge_intake"
QUEUE_FILE = REPORT_DIR / "proposed_records_queue.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _flag(name: str, default: str) -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _slug_time() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _urls(text: str) -> list[str]:
    hits = re.findall(r"https?://[^\s<>()\[\]{}\"']+", text or "")
    out: list[str] = []
    for h in hits:
        clean = h.rstrip('.,;:!?\")]}')
        if clean not in out:
            out.append(clean)
    return out


def _strip_html(html: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", " ", html or "", flags=re.IGNORECASE)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def _urls_from_html(html: str) -> list[str]:
    hrefs = re.findall(r"href\s*=\s*['\"](https?://[^'\"]+)['\"]", html or "", flags=re.IGNORECASE)
    out: list[str] = []
    for h in hrefs:
        clean = h.rstrip('.,;:!?\")]}')
        if clean not in out:
            out.append(clean)
    return out


def _extract_sender_email(sender: str) -> str:
    s = (sender or "").strip()
    m = re.search(r"<([^>]+@[^>]+)>", s)
    if m:
        return m.group(1).strip().lower()
    m2 = re.search(r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", s)
    if m2:
        return m2.group(1).strip().lower()
    return s.lower() or "unknown"


def _youtube(url: str) -> bool:
    u = (url or "").lower()
    return "youtube.com/" in u or "youtu.be/" in u


def _detect_category(subject: str, body: str) -> str:
    explicit = re.search(r"\bcategory\s*:\s*([a-zA-Z_\- ]{2,40})", body or "", flags=re.IGNORECASE)
    if explicit:
        raw = explicit.group(1).strip().lower().replace("-", "_").replace(" ", "_")
        mapping = {
            "funding": "funding",
            "credit": "credit",
            "marketing": "marketing",
            "grants": "grants",
            "grant": "grants",
            "opportunities": "opportunities",
            "opportunity": "opportunities",
            "trading": "trading",
            "business_setup": "business_setup",
            "business": "business_setup",
            "operations": "operations",
            "ai_workforce": "ai_workforce",
            "onboarding": "onboarding",
            "compliance": "compliance",
        }
        if raw in mapping:
            return mapping[raw]
    text = f"{subject} {body}".lower()
    rules = [
        ("funding", ["funding", "lender", "capital", "tier 1"]),
        ("credit", ["credit", "utilization", "fico", "inquiry", "tradeline"]),
        ("business_setup", ["llc", "ein", "naics", "duns", "business setup"]),
        ("grants", ["grant", "foundation", "rfa"]),
        ("opportunities", ["opportunity", "contract", "rfp", "partnership"]),
        ("marketing", ["marketing", "content", "social", "cta", "landing page"]),
        ("trading", ["trading", "forex", "spy", "btc", "eth", "paper trading"]),
        ("operations", ["operations", "dashboard", "runbook", "workflow"]),
        ("ai_workforce", ["ai workforce", "ai employee", "agent workflow"]),
        ("onboarding", ["onboarding", "signup", "invite flow"]),
        ("compliance", ["compliance", "disclaimer", "legal disclosure"]),
    ]
    for cat, keys in rules:
        if any(k in text for k in keys):
            return cat
    return "general"


def _extract_priority(body: str) -> str:
    text = (body or "").lower()
    if "priority: high" in text or "urgent" in text:
        return "high"
    if "priority: low" in text:
        return "low"
    return "medium"


def _extract_tags(body: str) -> list[str]:
    m = re.search(r"tags\s*:\s*(.+)", body or "", flags=re.IGNORECASE)
    if not m:
        return []
    parts = [p.strip().lower() for p in m.group(1).split(",") if p.strip()]
    out: list[str] = []
    for p in parts:
        if p not in out:
            out.append(p)
    return out[:12]


@dataclass
class ParsedKnowledgeEmail:
    sender: str
    subject: str
    timestamp: str
    email_message_id: str
    urls: list[str]
    youtube_links: list[str]
    notes: str
    requested_category: str
    priority: str
    tags: list[str]
    sender_email: str


def parse_knowledge_email(sender: str, subject: str, body: str, message_id: str = "") -> ParsedKnowledgeEmail:
    body_text = (body or "").strip()
    body_html = ""
    if "<html" in body_text.lower() or "<body" in body_text.lower() or "href=" in body_text.lower():
        body_html = body_text
        stripped = _strip_html(body_text)
        body_text = stripped or body_text
    urls = _urls(body_text)
    if body_html:
        for u in _urls_from_html(body_html):
            if u not in urls:
                urls.append(u)
    yts = [u for u in urls if _youtube(u)]
    sender_norm = (sender or "unknown").strip()
    subject_norm = (subject or "Knowledge Load").strip()
    sender_email = _extract_sender_email(sender_norm)
    return ParsedKnowledgeEmail(
        sender=sender_norm,
        subject=subject_norm,
        timestamp=_now(),
        email_message_id=(message_id or f"email-{hashlib.sha256((sender_norm + subject_norm + body_text).encode()).hexdigest()[:12]}"),
        urls=urls,
        youtube_links=yts,
        notes=body_text,
        requested_category=_detect_category(subject_norm, body_text),
        priority=_extract_priority(body_text),
        tags=_extract_tags(body_text),
        sender_email=sender_email,
    )


def parse_gmail_hydrated_message(message: dict[str, Any]) -> ParsedKnowledgeEmail:
    payload = message.get("payload") if isinstance(message.get("payload"), dict) else {}
    headers = payload.get("headers") if isinstance(payload.get("headers"), list) else []
    hmap: dict[str, str] = {}
    for h in headers:
        if isinstance(h, dict):
            hmap[str(h.get("name") or "").lower()] = str(h.get("value") or "")
    sender = hmap.get("from") or str(message.get("sender") or "")
    subject = hmap.get("subject") or str(message.get("subject") or "")
    message_id = hmap.get("message-id") or str(message.get("id") or message.get("message_id") or "")
    body_text = ""
    body_html = ""

    def _collect_parts(node: dict[str, Any]) -> None:
        nonlocal body_text, body_html
        mime = str(node.get("mimeType") or "").lower()
        b = node.get("body") if isinstance(node.get("body"), dict) else {}
        data = str(b.get("data") or "")
        if data:
            try:
                import base64

                decoded = base64.urlsafe_b64decode(data + "==").decode("utf-8", "replace")
            except Exception:
                decoded = ""
        else:
            decoded = ""
        if mime == "text/plain" and decoded:
            body_text += "\n" + decoded
        elif mime == "text/html" and decoded:
            body_html += "\n" + decoded
        for p in node.get("parts") or []:
            if isinstance(p, dict):
                _collect_parts(p)

    if payload:
        _collect_parts(payload)
    if not body_text and body_html:
        body_text = _strip_html(body_html)
    snippet = str(message.get("snippet") or "")
    merged = (body_text.strip() or _strip_html(body_html) or snippet).strip()
    parsed = parse_knowledge_email(sender=sender, subject=subject, body=merged, message_id=message_id)
    if body_html:
        extra = _urls_from_html(body_html)
        if extra:
            parsed.urls = list(dict.fromkeys(parsed.urls + extra))
            parsed.youtube_links = [u for u in parsed.urls if _youtube(u)]
    return parsed


def _dedup_key(url: str, category: str, source_email_id: str) -> str:
    base = f"{url}|{category}|{source_email_id}".encode()
    return hashlib.sha256(base).hexdigest()[:24]


def build_proposed_records(parsed: ParsedKnowledgeEmail, *, dry_run: bool = True) -> list[dict[str, Any]]:
    rows = []
    for url in parsed.urls:
        source_type = "youtube" if _youtube(url) else "website"
        rows.append(
            {
                "source_url": url,
                "source_type": source_type,
                "category": parsed.requested_category,
                "title": "pending_title_from_source",
                "summary": "pending_summary_from_source",
                "key_takeaways": [],
                "action_items": [],
                "confidence": "low",
                "created_at": _now(),
                "dry_run": bool(dry_run),
                "source_email_id": parsed.email_message_id,
                "dedup_key": _dedup_key(url, parsed.requested_category, parsed.email_message_id),
                "status": "proposed",
                "sender": parsed.sender,
                "sender_email": parsed.sender_email,
                "subject": parsed.subject,
                "received_at": parsed.timestamp,
                "links_count": len(parsed.urls),
            }
        )
    if parsed.notes:
        rows.append(
            {
                "source_url": "email_note",
                "source_type": "email_note",
                "category": parsed.requested_category,
                "title": "operator_note",
                "summary": parsed.notes[:500],
                "key_takeaways": [],
                "action_items": [],
                "confidence": "medium",
                "created_at": _now(),
                "dry_run": bool(dry_run),
                "source_email_id": parsed.email_message_id,
                "dedup_key": _dedup_key(parsed.notes[:120], parsed.requested_category, parsed.email_message_id),
                "status": "proposed",
                "sender": parsed.sender,
                "sender_email": parsed.sender_email,
                "subject": parsed.subject,
                "received_at": parsed.timestamp,
                "links_count": len(parsed.urls),
            }
        )
    return rows


def _load_queue() -> list[dict[str, Any]]:
    if QUEUE_FILE.exists():
        try:
            return json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_queue(rows: list[dict[str, Any]]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    QUEUE_FILE.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def ingest_knowledge_email_dry_run(sender: str, subject: str, body: str, message_id: str = "") -> dict[str, Any]:
    parsed = parse_knowledge_email(sender, subject, body, message_id=message_id)
    proposed = build_proposed_records(parsed, dry_run=True)
    queue = _load_queue()
    existing_keys = {str(r.get("dedup_key") or "") for r in queue}
    duplicates = [r for r in proposed if str(r.get("dedup_key") or "") in existing_keys]
    new_rows = [r for r in proposed if str(r.get("dedup_key") or "") not in existing_keys]
    queue.extend(new_rows)
    queue = queue[-1200:]
    _save_queue(queue)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORT_DIR / f"{_slug_time()}_email_knowledge_intake.md"
    lines = [
        "# Hermes Email Knowledge Intake (Dry-Run)",
        "",
        f"- timestamp: {_now()}",
        f"- sender: {parsed.sender}",
        f"- subject: {parsed.subject}",
        f"- message_id: {parsed.email_message_id}",
        f"- category_detected: {parsed.requested_category}",
        f"- priority: {parsed.priority}",
        f"- tags: {', '.join(parsed.tags) if parsed.tags else 'none'}",
        "",
        "## Links Found",
    ]
    if parsed.urls:
        lines.extend([f"- {u}" for u in parsed.urls])
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Duplicate Detection",
            f"- duplicates: {len(duplicates)}",
            f"- new_proposed_records: {len(new_rows)}",
            "",
            "## Proposed Knowledge Brain Records",
            f"- proposed_total: {len(proposed)}",
            "- mode: dry-run (no Supabase write)",
            "",
            "## Next Steps",
            "- Review proposed records in queue file.",
            "- Approve records before any storage path is enabled.",
            "- Keep HERMES_KNOWLEDGE_AUTO_STORE_ENABLED=false until manual sign-off.",
        ]
    )
    out.write_text("\n".join(lines), encoding="utf-8")

    return {
        "ok": True,
        "dry_run": True,
        "report_path": str(out),
        "category": parsed.requested_category,
        "urls_found": len(parsed.urls),
        "duplicates": len(duplicates),
        "proposed_records": len(proposed),
    }


def ingest_gmail_hydrated_email_dry_run(message: dict[str, Any]) -> dict[str, Any]:
    parsed = parse_gmail_hydrated_message(message)
    return ingest_knowledge_email_dry_run(
        sender=parsed.sender,
        subject=parsed.subject,
        body=parsed.notes,
        message_id=parsed.email_message_id,
    )


def recent_knowledge_email_intake(limit: int = 10) -> list[dict[str, Any]]:
    rows = _load_queue()
    return rows[-max(1, int(limit)):]
