#!/usr/bin/env python3
"""
Nexus Email Pipeline
Monitors raysnexusproject12221971@gmail.com via IMAP for [NEXUS] tagged emails.

Subject tags:
  [NEXUS] or [RESEARCH]  → extract YouTube URLs, run research pipeline, reply with summary
  [TASKS]                → parse task list, create coord_tasks entries, reply confirming
  [STATUS]               → run autonomy stack checks and reply with current operator status

Usage:
  python3 nexus_email_pipeline.py --once     # process inbox once and exit
  python3 nexus_email_pipeline.py            # run as daemon (polls every 2 min)

Required .env:
  NEXUS_EMAIL=raysnexusproject12221971@gmail.com
  NEXUS_EMAIL_PASSWORD=<16-char app password, no spaces>
"""

import os
import sys
import json
import time
import imaplib
import smtplib
import email
import subprocess
import re
import urllib.request
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

# Load .env manually so no dotenv package required
_env_file = Path(__file__).parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ[_k.strip()] = _v.strip()

NEXUS_EMAIL = os.getenv("NEXUS_EMAIL", "goclearonline@gmail.com")
NEXUS_EMAIL_PASSWORD = os.getenv("NEXUS_EMAIL_PASSWORD", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
NEXUS_DIR = Path(__file__).parent
RESEARCH_DIR = NEXUS_DIR / "workflows" / "research_ingestion"
AUTONOMY_CHECK = NEXUS_DIR / "scripts" / "check_autonomy_stack.sh"
AUTONOMY_STATUS = NEXUS_DIR / "scripts" / "autonomy_status.py"
POLL_INTERVAL = int(os.getenv("EMAIL_POLL_INTERVAL", "120"))

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY", "")

IMAP_HOST = "imap.gmail.com"
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

YT_RE = re.compile(
    r'https?://(?:www\.)?(?:youtube\.com/(?:watch\?v=[\w-]+|shorts/[\w-]+)|youtu\.be/[\w-]+)(?:[^\s<>"]*)?'
)
TASK_RE = re.compile(r'^\s*(?:\d+[.)]\s+|-\s+|\*\s+)(.+)', re.MULTILINE)


# ── IMAP helpers ──────────────────────────────────────────────────────────────

def fetch_unread_nexus_emails():
    with imaplib.IMAP4_SSL(IMAP_HOST) as imap:
        imap.login(NEXUS_EMAIL, NEXUS_EMAIL_PASSWORD)
        imap.select("INBOX")

        _, ids = imap.search(None, 'UNSEEN SUBJECT "nexus"')
        _, ids2 = imap.search(None, 'UNSEEN SUBJECT "research"')
        _, ids3 = imap.search(None, 'UNSEEN SUBJECT "tasks"')
        _, ids4 = imap.search(None, 'UNSEEN SUBJECT "status"')

        all_ids = set()
        for id_list in [ids, ids2, ids3, ids4]:
            for i in id_list[0].split():
                all_ids.add(i)

        messages = []
        for uid in all_ids:
            _, data = imap.fetch(uid, "(RFC822)")
            raw = data[0][1]
            msg = email.message_from_bytes(raw)
            body = extract_body(msg)
            messages.append({
                "uid": uid,
                "subject": msg.get("Subject", ""),
                "sender": msg.get("From", ""),
                "reply_to": msg.get("Reply-To") or msg.get("From", ""),
                "body": body,
            })

            # Mark as read
            imap.store(uid, "+FLAGS", "\\Seen")

        return messages


def extract_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                return part.get_payload(decode=True).decode("utf-8", errors="replace")
    else:
        return msg.get_payload(decode=True).decode("utf-8", errors="replace")
    return ""


# ── SMTP sender ───────────────────────────────────────────────────────────────

def send_reply(to, subject, body):
    re_subject = subject if subject.startswith("Re:") else f"Re: {subject}"
    msg = MIMEText(body)
    msg["From"] = NEXUS_EMAIL
    msg["To"] = to
    msg["Subject"] = re_subject

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(NEXUS_EMAIL, NEXUS_EMAIL_PASSWORD)
        smtp.send_message(msg)
    print(f"[email] Reply sent to {to}")


def summarize_autonomy_status(raw_output):
    lines = raw_output.splitlines()
    summary = []

    or_ok = any("PASS" in line and "model=" in line for line in lines)
    gmail_ok = any("PASS" in line and "@gmail.com" in line for line in lines)
    email_line = next((line.strip() for line in lines if "Email pipeline" in line), "")
    scheduler_line = next((line.strip() for line in lines if "Scheduler" in line), "")
    hermes_line = next((line.strip() for line in lines if "Hermes gateway" in line), "")

    if or_ok and gmail_ok:
        summary.append("Overall: the main autonomy path is healthy.")
    else:
        summary.append("Overall: the autonomy path needs attention.")

    summary.append(
        "Model access: OpenRouter is connected and responding."
        if or_ok else
        "Model access: OpenRouter is not passing its health check."
    )
    summary.append(
        "Email: Gmail authentication is working."
        if gmail_ok else
        "Email: Gmail authentication is failing."
    )

    if "last_exit=0" in email_line:
        summary.append("Email worker: healthy. It runs as a one-shot job and exits cleanly between checks.")
    elif email_line:
        summary.append(f"Email worker: {email_line}")

    if "state=running" in scheduler_line:
        summary.append("Scheduler: running scheduled jobs normally.")
    elif scheduler_line:
        summary.append(f"Scheduler: {scheduler_line}")

    if "state=running" in hermes_line:
        summary.append("Hermes gateway: process is running.")
    elif hermes_line:
        summary.append(f"Hermes gateway: {hermes_line}")

    # These are separate from Hermes Telegram polling and can still send outbound notices.
    aux_paths = []
    if (NEXUS_DIR / "operations_center" / "scheduler.py").exists():
        aux_paths.append("scheduler alerts")
    if (NEXUS_DIR / "coordination" / "coordination_worker.py").exists():
        aux_paths.append("coordination alerts")
    if (NEXUS_DIR / "ceo_agent" / "ceo_worker.py").exists():
        aux_paths.append("CEO briefings")

    if aux_paths:
        summary.append(
            "Other processes: Telegram-capable notification paths still exist for "
            + ", ".join(aux_paths)
            + ". These are separate from the Hermes Telegram gateway."
        )

    return "\n".join(summary)


def format_autonomy_status_email(raw_output):
    lines = raw_output.splitlines()

    def normalize_launch_agent_line(line, label):
        if not line:
            return "unknown"
        compact = " ".join(line.split())
        if "state=not running" in compact and "last_exit=0" in compact:
            return f"{label}: idle between checks (last exit 0)"
        return compact

    def first_match(pattern):
        for line in lines:
            if re.search(pattern, line):
                return line.strip()
        return ""

    openrouter_line = first_match(r"PASS.*model=") or first_match(r"FAIL.*model=")
    gmail_line = first_match(r"PASS.*@gmail\.com") or first_match(r"FAIL.*gmail")
    email_line = normalize_launch_agent_line(first_match(r"Email pipeline"), "Email pipeline")
    scheduler_line = normalize_launch_agent_line(first_match(r"Scheduler"), "Scheduler")
    hermes_line = normalize_launch_agent_line(first_match(r"Hermes gateway"), "Hermes gateway")

    recent = []
    capture_recent = False
    for line in lines:
        stripped = line.strip()
        if stripped == "Recent Signals":
            capture_recent = True
            continue
        if capture_recent and stripped.startswith("==="):
            continue
        if capture_recent and stripped == "Summary":
            break
        if capture_recent and stripped:
            recent.append(stripped)

    recent = recent[-3:]
    plain_summary = summarize_autonomy_status(raw_output)

    body_lines = [
        "Nexus Status",
        "",
        "Operator summary:",
        plain_summary,
        "",
        "Current checks:",
        f"- OpenRouter: {openrouter_line or 'unknown'}",
        f"- Gmail auth: {gmail_line or 'unknown'}",
        f"- {email_line}",
        f"- {scheduler_line}",
        f"- {hermes_line}",
    ]

    if recent:
        body_lines.extend([
            "",
            "Recent activity:",
        ])
        for line in recent:
            body_lines.append(f"- {line}")

    body_lines.extend([
        "",
        "Reply with [TASKS] to create work items or [STATUS] again for a fresh check.",
    ])

    return "\n".join(body_lines)


# ── Supabase artifact fetch ───────────────────────────────────────────────────

def fetch_recent_artifacts(since_iso):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return []
    url = (
        f"{SUPABASE_URL}/rest/v1/research_artifacts"
        f"?created_at=gte.{since_iso}&order=created_at.desc&limit=20"
    )
    req = urllib.request.Request(url, headers={
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"[supabase] Fetch failed: {e}")
        return []


# ── Groq recommendation writer ────────────────────────────────────────────────

TOPIC_ACTION = {
    "trading": "flagged for strategy testing in the trading engine",
    "credit_repair": "stored in the credit repair knowledge base",
    "grant_research": "added to the grants database for review",
    "business_opportunities": "logged as a business opportunity for evaluation",
    "crm_automation": "stored in the CRM/automation playbook",
    "general_business_intelligence": "stored in general business intelligence",
}


def build_recommendation_email(artifacts, url_count):
    if not artifacts:
        return "Pipeline ran but no results were stored. The video may have no captions or failed to download."

    lines = []
    for i, a in enumerate(artifacts, 1):
        topic = a.get("topic", "unknown")
        title = a.get("title", "Untitled")
        summary = a.get("summary") or "No summary available."
        key_points = a.get("key_points") or []
        action_items = a.get("action_items") or []
        opportunities = a.get("opportunity_notes") or []
        risks = a.get("risk_warnings") or []
        disposition = TOPIC_ACTION.get(topic, "stored in Nexus knowledge base")

        lines.append(f"{'='*50}")
        lines.append(f"Video {i}: {title}")
        lines.append(f"Category: {topic.replace('_', ' ').title()}")
        lines.append(f"")
        lines.append(f"Summary:")
        lines.append(f"{summary}")

        if key_points:
            lines.append(f"\nKey Points:")
            for p in key_points[:5]:
                lines.append(f"  • {p}")

        if opportunities:
            lines.append(f"\nOpportunities:")
            for o in opportunities[:3]:
                lines.append(f"  + {o}")

        if action_items:
            lines.append(f"\nAction Items:")
            for ai in action_items[:4]:
                lines.append(f"  → {ai}")

        if risks:
            lines.append(f"\nRisks / Warnings:")
            for r in risks[:2]:
                lines.append(f"  ⚠ {r}")

        lines.append(f"\nNexus Recommendation:")
        lines.append(f"  This content has been {disposition}.")

        if topic == "trading":
            lines.append(f"  Run: python3 nexus_coord.py add-task codex 'Test strategy from: {title[:60]}'")
        elif topic == "grant_research":
            lines.append(f"  Check Supabase research_artifacts table for grant details and deadlines.")
        elif topic == "credit_repair":
            lines.append(f"  Content stored — Hermes can retrieve it for client sessions.")

        lines.append("")

    return "\n".join(lines)


def groq_enhance(raw_recommendation):
    if not GROQ_API_KEY or not raw_recommendation:
        return raw_recommendation

    prompt = (
        "You are writing a professional but friendly email from the Nexus AI system to its owner.\n"
        "Below is structured research output. Rewrite it as a clean, readable email body — "
        "keep all the facts and recommendations, improve the flow and tone. Under 400 words.\n\n"
        f"{raw_recommendation[:2500]}"
    )
    payload = json.dumps({
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 500,
        "temperature": 0.4,
    }).encode()
    req = urllib.request.Request(
        f"{GROQ_BASE_URL}/chat/completions",
        data=payload,
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[groq] Enhancement failed: {e}")
        return raw_recommendation


# ── Research pipeline ─────────────────────────────────────────────────────────

def process_research(msg):
    urls = list(dict.fromkeys(YT_RE.findall(msg["body"])))
    if not urls:
        send_reply(msg["reply_to"], msg["subject"],
                   "Nexus received your email but found no YouTube URLs to process.\n\n"
                   "Paste YouTube links in the email body and resend with [NEXUS] in the subject.")
        return

    sources = [
        {"type": "youtube_video", "topic": "general_business_intelligence",
         "name": "Email submission", "url": url, "max_videos": 1}
        for url in urls
    ]

    uid_str = msg["uid"].decode() if isinstance(msg["uid"], bytes) else str(msg["uid"])
    drop_file = RESEARCH_DIR / "drop_in" / f"email_{uid_str}.json"
    drop_file.write_text(json.dumps({"sources": sources}, indent=2))

    print(f"[email] Research pipeline — {len(urls)} URL(s)...")
    since = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")

    result = subprocess.run(
        ["node", "research_ingestion_runner.js", "--mode", "batch",
         "--sources", str(drop_file)],
        cwd=str(RESEARCH_DIR),
        capture_output=True, text=True, timeout=300,
    )

    if result.returncode != 0:
        print(f"[email] Pipeline stderr: {result.stderr[:200]}")

    # Pull real results from Supabase instead of parsing log output
    artifacts = fetch_recent_artifacts(since)
    raw = build_recommendation_email(artifacts, len(urls))
    body = groq_enhance(raw)

    send_reply(
        msg["reply_to"], msg["subject"],
        f"Nexus Research — {len(artifacts)} Result(s) Ready\n\n"
        f"{body}\n\n"
        f"---\n"
        f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"All results stored in Supabase. Agents have access."
    )


# ── Task pipeline ─────────────────────────────────────────────────────────────

def process_tasks(msg):
    raw = TASK_RE.findall(msg["body"])
    tasks = [t.strip() for t in raw if len(t.strip()) > 3]

    if not tasks:
        send_reply(msg["reply_to"], msg["subject"],
                   "Nexus received your email but found no tasks.\n\n"
                   "Use a numbered list or bullet points, e.g.:\n"
                   "1. Build the login page\n2. Fix the API timeout\n\n"
                   "Put [TASKS] in the subject line.")
        return

    created = []
    for task_text in tasks:
        tl = task_text.lower()
        if any(w in tl for w in ["code", "backend", "api", "database", "supabase", "python", "script"]):
            agent = "claude-code"
        elif any(w in tl for w in ["frontend", "ui", "design", "component", "react", "page", "style"]):
            agent = "codex"
        else:
            agent = "all"

        r = subprocess.run(
            ["python3", "nexus_coord.py", "add-task", agent, task_text],
            cwd=str(NEXUS_DIR), capture_output=True, text=True,
        )
        created.append(f"  [{agent}] {task_text}")

    task_lines = "\n".join(created)
    send_reply(
        msg["reply_to"], msg["subject"],
        f"Nexus Task Queue — {len(created)} Task(s) Created\n\n"
        f"{task_lines}\n\n"
        f"Agents pick these up on their next check.\n"
        f"For a live stack check, email back with [STATUS] in the subject.\n\n"
        f"---\n"
        f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )


def process_status(msg):
    if not AUTONOMY_CHECK.exists():
        send_reply(
            msg["reply_to"], msg["subject"],
            "Nexus Status — check unavailable\n\n"
            "The autonomy check script is missing.\n\n"
            f"Expected at: {AUTONOMY_CHECK}"
        )
        return

    result = subprocess.run(
        [str(AUTONOMY_CHECK)],
        cwd=str(NEXUS_DIR),
        capture_output=True,
        text=True,
        timeout=90,
    )

    output = (result.stdout or "").strip()
    if result.returncode != 0:
        error = (result.stderr or "").strip()
        body = (
            "Nexus Status — check failed\n\n"
            f"{output[:2500]}\n"
        )
        if error:
            body += f"\nErrors:\n{error[:1200]}\n"
    else:
        body = format_autonomy_status_email(output)

    send_reply(
        msg["reply_to"],
        msg["subject"],
        f"{body}\n\n---\nChecked: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )


# ── Mode detection ────────────────────────────────────────────────────────────

def detect_mode(subject, body):
    s = subject.lower().strip()
    if "[status]" in s or s == "status" or s.startswith("re: [status]"):
        return "status"
    if "[tasks]" in s or s == "tasks" or s.startswith("re: [tasks]"):
        return "tasks"
    if "[nexus]" in s or "[research]" in s:
        return "research" if YT_RE.search(body) else None
    return None


# ── Poll ──────────────────────────────────────────────────────────────────────

def poll_once():
    messages = fetch_unread_nexus_emails()
    if not messages:
        return 0

    for msg in messages:
        sender_lower = (msg.get("sender") or "").lower()
        if NEXUS_EMAIL.lower() in sender_lower:
            print(f"[email] Skipping self-sent message — {msg['subject'][:60]}")
            continue
        mode = detect_mode(msg["subject"], msg["body"])
        if not mode:
            continue
        print(f"[email] {mode.upper()} from {msg['sender'][:40]} — {msg['subject'][:50]}")
        try:
            if mode == "research":
                process_research(msg)
            elif mode == "tasks":
                process_tasks(msg)
            elif mode == "status":
                process_status(msg)
        except Exception as e:
            print(f"[email] Error: {e}")

    return len(messages)


def run_daemon():
    if not NEXUS_EMAIL_PASSWORD:
        print("ERROR: NEXUS_EMAIL_PASSWORD not set in .env")
        sys.exit(1)
    print(f"[email] Nexus Email Pipeline — polling {NEXUS_EMAIL} every {POLL_INTERVAL}s")
    while True:
        try:
            count = poll_once()
            if count:
                print(f"[email] Processed {count} email(s) at {datetime.now().strftime('%H:%M:%S')}")
        except Exception as e:
            print(f"[email] Poll error: {e}")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    if "--once" in sys.argv:
        n = poll_once()
        print(f"Done — {n} email(s) processed")
    else:
        run_daemon()
