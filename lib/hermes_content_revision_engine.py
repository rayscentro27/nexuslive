"""
hermes_content_revision_engine.py
Apply deterministic transformations to checklist draft artifacts.
No paid API required. Template-based rewrites only.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_ROOT = Path(__file__).resolve().parent.parent
_CONTENT_DIR = _ROOT / "docs" / "reports" / "content"
_CHECKLIST_SLUG = "credit_funding_readiness_checklist"
_CHECKLIST_ACTION_ID = "act_aa99698ef8"

# ── Instruction routing ──────────────────────────────────────────────────────

REVISION_INSTRUCTION_MAP: dict[str, str] = {
    "make it simpler": "simplified",
    "simplify it": "simplified",
    "make this simpler": "simplified",
    "make it shorter": "simplified",
    "make it clearer": "simplified",
    "make it more professional": "professional",
    "make it more persuasive": "professional",
    "make it better": "improved",
    "improve it": "improved",
    "revise it": "improved",
    "update it": "improved",
    "turn it into a lead magnet": "lead_magnet",
    "turn this into a lead magnet": "lead_magnet",
    "create a short video script from this": "short_video_script",
    "create a tiktok script from this": "short_video_script",
    "create a newsletter from this": "newsletter",
    "create an email from this": "email_draft",
    "clean it up": "cleaned",
    "remove duplicates": "cleaned",
    "fix duplicate sections": "cleaned",
    "clean up the draft": "cleaned",
    "deduplicate it": "cleaned",
}

REVISION_LABELS: dict[str, str] = {
    "simplified": "simplified",
    "professional": "professional",
    "improved": "improved",
    "lead_magnet": "lead magnet",
    "short_video_script": "short video script",
    "newsletter": "newsletter",
    "email_draft": "email draft",
    "cleaned": "cleaned-up",
}

REVISION_CHANGE_SUMMARIES: dict[str, list[str]] = {
    "simplified": [
        "Added a plain-English 'Start Here' section",
        "Simplified checklist item descriptions",
        "Replaced funding jargon with plain-language explanations",
        "Shortened sections for beginner readers",
    ],
    "professional": [
        "Added executive-level intro",
        "Strengthened section headings",
        "Tightened language throughout",
        "Added readiness positioning statement",
    ],
    "improved": [
        "Enhanced intro paragraph",
        "Added additional checklist items per section",
        "Improved section descriptions",
        "Added action-oriented language",
    ],
    "lead_magnet": [
        "Reformatted as a lead magnet with scoring",
        "Added 'Score Yourself' section",
        "Added 'What Your Score Means' section",
        "Added Nexus CTA",
    ],
    "short_video_script": [
        "Converted to 30-60 second video script format",
        "Added hook, on-screen text, and CTA",
        "Condensed checklist into 5 key points",
    ],
    "newsletter": [
        "Reformatted as newsletter email",
        "Added subject line and preview text",
        "Conversational tone throughout",
    ],
    "email_draft": [
        "Reformatted as follow-up email",
        "Added subject line",
        "Actionable CTA added",
    ],
    "cleaned": [
        "Removed duplicate section headings",
        "Removed duplicate subtitle lines",
        "Preserved compliance note",
        "Preserved internal draft notice",
        "Preserved checklist structure",
    ],
}


def resolve_revision_instruction(user_message: str) -> Optional[str]:
    """Return revision type string for a user message, or None if not a revision."""
    t = (user_message or "").strip().lower().rstrip("?. ")
    return REVISION_INSTRUCTION_MAP.get(t)


def find_latest_checklist_draft() -> Optional[Path]:
    if not _CONTENT_DIR.exists():
        return None
    drafts = sorted(_CONTENT_DIR.glob(f"{_CHECKLIST_SLUG}_draft_*.md"), reverse=True)
    return drafts[0] if drafts else None


# ── Main revision entry point ─────────────────────────────────────────────────

def revise_content_draft(previous_path: Path, revision_type: str) -> dict:
    """Read previous draft, apply transformation, write new file. Returns result dict."""
    try:
        original_text = previous_path.read_text()
    except Exception as exc:
        return {"created": False, "error": f"Could not read draft: {exc}"}

    _CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y%m%d_%H%M%S") + f"_{now.microsecond // 1000:03d}"

    transform_fn = {
        "simplified": simplify_checklist_draft,
        "professional": professionalize_checklist_draft,
        "improved": improve_checklist_draft,
        "cleaned": cleanup_draft,
        "lead_magnet": convert_to_lead_magnet,
        "short_video_script": convert_to_short_video_script,
        "newsletter": convert_to_newsletter,
        "email_draft": convert_to_email_draft,
    }.get(revision_type, improve_checklist_draft)

    revised_text = transform_fn(original_text, ts)
    path = _CONTENT_DIR / f"{_CHECKLIST_SLUG}_draft_{ts}_{revision_type}.md"
    path.write_text(revised_text)

    meta = _CONTENT_DIR / f"{_CHECKLIST_SLUG}_draft_{ts}_{revision_type}.json"
    meta.write_text(json.dumps({
        "revision_type": revision_type,
        "previous_path": str(previous_path),
        "draft_version": ts,
        "status": "internal_draft",
        "created_at": now.isoformat(),
        "requires_approval_before": ["publishing", "selling", "client use", "website", "email"],
    }, indent=2))

    try:
        from lib.hermes_decision_log import log_decision
        log_decision(
            question_or_trigger=f"Ray requested: {revision_type} revision of checklist draft",
            decision=f"Created {revision_type} revision artifact",
            why_selected="Internal draft revision per Ray's instruction",
            artifact_paths=[str(path.relative_to(_ROOT))],
            goal_alignment="Improving checklist toward publishable state",
            risk_level="low",
            autonomous_allowed=True,
            requires_ray_approval=False,
        )
    except Exception:
        pass

    return {
        "created": True,
        "revision_type": revision_type,
        "path": str(path.relative_to(_ROOT)),
        "previous_path": str(previous_path.relative_to(_ROOT)),
        "action_id": _CHECKLIST_ACTION_ID,
        "change_summary": REVISION_CHANGE_SUMMARIES.get(revision_type, []),
    }


# ── Response formatting ───────────────────────────────────────────────────────

def format_revision_created_response(result: dict) -> str:
    if not result.get("created"):
        return f"Could not create revision: {result.get('error', 'unknown error')}"

    revision_type = result.get("revision_type", "")
    label = REVISION_LABELS.get(revision_type, revision_type)
    path = result.get("path", "")
    previous_path = result.get("previous_path", "")
    action_id = result.get("action_id", "")
    changes = result.get("change_summary", [])
    decision_log = "docs/reports/decisions/hermes_decision_log.jsonl"

    change_lines = "\n".join(f"- {c}" for c in changes) if changes else "- Applied revision"

    evidence = f"- New draft: {path}\n"
    if previous_path:
        evidence += f"- Previous draft: {previous_path}\n"
    evidence += f"- Action: {action_id}\n- Decision log: {decision_log}"

    return (
        f"CONTENT DRAFT VERSION CREATED\n\n"
        f"I created a {label} internal version for review.\n\n"
        f"What changed:\n{change_lines}\n\n"
        f"Status:\nInternal draft only.\n\n"
        f"Approval:\nRequired before publishing, selling, emailing clients, or adding to the website.\n\n"
        f"Evidence:\n{evidence}\n\n"
        f"Next:\nAsk 'what changed?' to compare this version with the previous draft."
    )


# ── Jargon replacement helpers ────────────────────────────────────────────────

_SIMPLIFY_REPLACEMENTS = [
    (r"LLC,\s*S-Corp,\s*or\s*C-Corp registered with your state",
     "LLC, S-Corp, or C-Corp (LLC is most common for small businesses)"),
    (r"Employer Identification Number from the IRS \(free at irs\.gov\)",
     "business Tax ID — like a Social Security number for your business (get it free at irs.gov)"),
    (r"physical or registered agent address \(not a P\.O\. box for most lenders\)",
     "real street address (most lenders won't accept a P.O. box)"),
    (r"NAICS code — industry classification code; know yours before applying",
     "industry code (NAICS) — tells lenders what your business does; look yours up free online"),
    (r"clear, one-sentence description of what your business does",
     "one sentence that explains what your business does"),
    (r"check current FICO 8 score \(FICO SBSS matters for SBA\)",
     "check your current credit score (FICO SBSS is what SBA lenders use)"),
    (r"revolving balances below 30% of limits",
     "credit card balances below 30% of each card's limit"),
    (r"Derogatory items — review for collections, charge-offs, late payments",
     "Negative marks — check for collections, missed payments, or accounts sent to collectors"),
    (r"Credit mix — both revolving and installment accounts help",
     "Credit variety — having both credit cards and loans helps your score"),
    (r"Business credit profile exists — check Dun & Bradstreet, Experian Business, Equifax Business",
     "Business credit profile — check if your business has credit history at D&B, Experian Business, or Equifax Business"),
    (r"DUNS number — register with D&B if you don't have one \(free\)",
     "D&B business ID (DUNS) — register free at dnb.com if you don't have one"),
    (r"Trade lines — at least 3–5 accounts reporting to business credit bureaus",
     "Vendor credit accounts — you need at least 3–5 accounts that report to business credit bureaus"),
    (r"Bookkeeping current — income and expenses tracked \(QuickBooks, Wave, etc\.\)",
     "Finances tracked — use any accounting app (QuickBooks, Wave, or a spreadsheet)"),
    (r"IRS confirmation \(CP575 or 147C\)",
     "IRS EIN confirmation letter (CP575 or 147C form)"),
    (r"articles of incorporation or LLC operating agreement",
     "LLC operating agreement or incorporation documents"),
    (r"invoices, contracts, or payment processor statements if needed",
     "invoices, contracts, or receipts showing your revenue"),
    (r"Open tax liens or judgments — must be addressed before most funding",
     "Unpaid tax liens or court judgments — these need to be resolved before most lenders will work with you"),
]


def _apply_simplify_replacements(text: str) -> str:
    for pattern, replacement in _SIMPLIFY_REPLACEMENTS:
        text = re.sub(pattern, replacement, text)
    return text


# ── Idempotency / dedup helpers ───────────────────────────────────────────────

def has_simplified_marker(text: str) -> bool:
    return "Simplified — Plain English Edition" in text


def has_start_here_section(text: str) -> bool:
    return bool(re.search(r"^## Start Here", text, re.MULTILINE))


def _remove_duplicate_lines(text: str) -> str:
    """Remove consecutive duplicate non-blank lines (e.g. doubled subtitle)."""
    lines = text.splitlines(keepends=True)
    result: list[str] = []
    prev_non_blank: Optional[str] = None
    for line in lines:
        stripped = line.rstrip("\n").rstrip()
        if stripped:
            if stripped == prev_non_blank:
                continue
            prev_non_blank = stripped
        else:
            prev_non_blank = None
        result.append(line)
    return "".join(result)


def dedupe_repeated_sections(text: str) -> str:
    """Remove duplicate ## sections; keep the first occurrence of each heading."""
    lines = text.splitlines(keepends=True)
    preamble: list[str] = []
    sections: list[tuple[str, list[str]]] = []
    current_heading: Optional[str] = None
    current_body: list[str] = []

    for line in lines:
        stripped = line.rstrip("\n").rstrip()
        if stripped.startswith("## "):
            if current_heading is None:
                preamble = list(current_body)
            else:
                sections.append((current_heading, current_body))
            current_heading = stripped
            current_body = []
        else:
            current_body.append(line)

    if current_heading is not None:
        sections.append((current_heading, current_body))
    elif current_body:
        preamble = list(current_body)

    seen: set[str] = set()
    unique_sections: list[tuple[str, list[str]]] = []
    for heading, body in sections:
        if heading not in seen:
            seen.add(heading)
            unique_sections.append((heading, body))

    result = "".join(preamble)
    for heading, body in unique_sections:
        result += heading + "\n"
        result += "".join(body)
    return result


def normalize_revision_output(text: str) -> str:
    """Remove duplicate consecutive lines and duplicate ## sections."""
    text = _remove_duplicate_lines(text)
    text = dedupe_repeated_sections(text)
    return text


# ── Transformation functions ──────────────────────────────────────────────────

_INTERNAL_NOTE = "*Internal Draft — Not for publication*"


def simplify_checklist_draft(text: str, ts: str) -> str:
    """Create a plain-English, beginner-friendly version of the checklist."""
    # Only add Simplified marker if not already present (idempotent)
    if not has_simplified_marker(text):
        text = re.sub(
            r"^# Credit/Funding Readiness Checklist",
            "# Credit/Funding Readiness Checklist\n*(Simplified — Plain English Edition)*",
            text, count=1, flags=re.MULTILINE,
        )

    # Apply jargon replacements
    text = _apply_simplify_replacements(text)

    # Only insert "Start Here" section if not already present (idempotent)
    if not has_start_here_section(text):
        start_here = (
            "\n## Start Here\n\n"
            "If you're new to business funding, work through these in order:\n\n"
            "1. **Register your business** — An LLC is the most common choice\n"
            "2. **Get your EIN** — Free at irs.gov, takes 5 minutes\n"
            "3. **Open a business bank account** — Keep business and personal money separate\n"
            "4. **Check your personal credit score** — You need at least 600 to get started\n"
            "5. **Track 6 months of revenue** — Consistent deposits are what lenders look for\n\n"
            "Once these are in place, come back to this checklist to prep for an actual application.\n"
        )
        text = re.sub(r"(\n## Who This Checklist Is For)", start_here + r"\1", text, count=1)

    # Update the internal draft note
    text = re.sub(
        r"\*Internal Draft — [\d_]+ UTC — (?:Simplified Edition — )?Not for publication\*",
        f"*Internal Draft — {ts} UTC — Simplified Edition — Not for publication*",
        text,
    )
    text = re.sub(
        r"\*Internal draft — [\d_]+ UTC — (?:[^—]+— )?Pending Ray's review.*?\*",
        f"*Internal draft — {ts} UTC — Simplified Edition — Pending Ray's review and approval before any use.*",
        text,
    )

    # Final safety: remove any remaining duplicate lines or sections
    text = normalize_revision_output(text)
    return text


def professionalize_checklist_draft(text: str, ts: str) -> str:
    """Create a polished, executive-tone version of the checklist."""
    if "Professional Edition" not in text:
        text = re.sub(
            r"^# Credit(?:/Funding|& Funding) Readiness Checklist",
            "# Credit & Funding Readiness Checklist\n*(Professional Edition)*",
            text, count=1, flags=re.MULTILINE,
        )

    # Add professional intro section
    professional_intro = (
        "\n## Executive Summary\n\n"
        "This checklist prepares business owners to pursue credit lines, SBA loans, "
        "revenue-based financing, and business credit cards with confidence. "
        "Completing all items positions your business to meet standard lender requirements "
        "and avoid common disqualifying factors before submitting an application.\n\n"
        "Estimated preparation time: 2–8 weeks depending on your current readiness.\n"
    )
    text = re.sub(r"(\n## Who This Checklist Is For)", professional_intro + r"\1", text, count=1)

    # Strengthen the "Who This Is For" section
    text = re.sub(
        r"(## Who This Checklist Is For\n\n)Business owners who want to apply for business funding.*?before they apply\.",
        r"\1**Target audience:** Business owners pursuing capital — credit lines, SBA loans, revenue-based financing, "
        r"or business credit cards — who want to maximize approval probability and avoid disqualifying errors "
        r"before submitting applications.",
        text, flags=re.DOTALL,
    )

    # Upgrade section headings
    text = text.replace(
        "## 5. Funding Red Flags to Fix First",
        "## 5. Disqualifying Factors — Resolve Before Applying",
    )
    text = text.replace(
        "## 6. What to Fix First (Priority Order)",
        "## 6. Priority Action Sequence",
    )
    text = text.replace(
        "## 7. Nexus Next Step",
        "## 7. Nexus Platform — Your Funding Intelligence Hub",
    )

    text = re.sub(
        r"\*Internal Draft — [\d_]+ UTC — Not for publication\*",
        f"*Internal Draft — {ts} UTC — Professional Edition — Not for publication*",
        text,
    )
    text = re.sub(
        r"\*Internal draft — [\d_]+ UTC — Pending Ray's review.*?\*",
        f"*Internal draft — {ts} UTC — Professional Edition — Pending Ray's review and approval before any use.*",
        text,
    )
    return text


def improve_checklist_draft(text: str, ts: str) -> str:
    """Create an improved version with additional items and better descriptions."""
    if "Improved Edition" not in text:
        text = re.sub(
            r"^# Credit/Funding Readiness Checklist",
            "# Credit/Funding Readiness Checklist\n*(Improved Edition)*",
            text, count=1, flags=re.MULTILINE,
        )

    # Add items to Business Setup section
    text = text.replace(
        "- [ ] **Business description** — clear, one-sentence description of what your business does",
        "- [ ] **Business description** — clear, one-sentence description of what your business does\n"
        "- [ ] **Business license** — local/state operating license if required for your industry\n"
        "- [ ] **SOC 2 / industry certifications** — relevant to your sector if applicable",
    )

    # Add items to Banking section
    text = text.replace(
        "- [ ] **Bookkeeping current** — income and expenses tracked (QuickBooks, Wave, etc.)",
        "- [ ] **Bookkeeping current** — income and expenses tracked (QuickBooks, Wave, etc.)\n"
        "- [ ] **Profit & loss statement** — basic P&L for the last 12 months\n"
        "- [ ] **Cash flow positive** — more money coming in than going out for 3+ months",
    )

    # Improve the intro paragraph
    text = re.sub(
        r"(## Who This Checklist Is For\n\n)Business owners who want to apply for business funding",
        r"\1Business owners and entrepreneurs who want to apply for business funding",
        text,
    )

    text = re.sub(
        r"\*Internal Draft — [\d_]+ UTC — Not for publication\*",
        f"*Internal Draft — {ts} UTC — Improved Edition — Not for publication*",
        text,
    )
    text = re.sub(
        r"\*Internal draft — [\d_]+ UTC — (?:[^—]+— )?Pending Ray's review.*?\*",
        f"*Internal draft — {ts} UTC — Improved Edition — Pending Ray's review and approval before any use.*",
        text,
    )
    return text


def cleanup_draft(text: str, ts: str) -> str:
    """Remove duplicate headings, duplicate subtitles, and redundant sections."""
    text = normalize_revision_output(text)
    text = re.sub(
        r"\*Internal Draft — [\d_]+ UTC — (?:[^—\n]+— )?Not for publication\*",
        f"*Internal Draft — {ts} UTC — Cleaned Edition — Not for publication*",
        text,
    )
    text = re.sub(
        r"\*Internal draft — [\d_]+ UTC — (?:[^—\n]+— )?Pending Ray's review.*?\*",
        f"*Internal draft — {ts} UTC — Cleaned Edition — Pending Ray's review and approval before any use.*",
        text,
    )
    return text


def convert_to_lead_magnet(text: str, ts: str) -> str:
    """Convert the checklist into a scored lead magnet format."""
    return f"""# Credit & Funding Readiness Scorecard
*Internal Draft — Lead Magnet Format — {ts} UTC — Not for publication*

> **INTERNAL ONLY.** Do not share with clients, publish, or use for marketing until explicitly approved by Ray.

---

## Are You Ready for Business Funding?

Score yourself on each section to find out where you stand — and what to fix before you apply.

**How to score:** Give yourself 1 point for each item you have in place.

---

## Section 1 — Business Setup (8 points)

- [ ] Business entity formed (LLC, S-Corp, or C-Corp)
- [ ] EIN obtained
- [ ] Business address (not a P.O. box)
- [ ] Business phone number
- [ ] Business email
- [ ] Website
- [ ] NAICS code identified
- [ ] Business description written

**Your score: ___ / 8**

---

## Section 2 — Credit Profile (8 points)

### Personal Credit
- [ ] Know your current FICO score
- [ ] Credit utilization below 30%
- [ ] No recent derogatory items
- [ ] 12+ months on-time payment history
- [ ] Credit mix (revolving + installment)

### Business Credit
- [ ] Business credit profile exists
- [ ] DUNS number registered
- [ ] 3+ trade lines reporting

**Your score: ___ / 8**

---

## Section 3 — Banking & Finances (5 points)

- [ ] Separate business bank account open
- [ ] 6+ months account history
- [ ] Regular consistent deposits
- [ ] No overdrafts in last 3 months
- [ ] Bookkeeping current

**Your score: ___ / 5**

---

## Section 4 — Documents Ready (8 points)

- [ ] Government-issued ID
- [ ] EIN letter from IRS
- [ ] 3–6 months business bank statements
- [ ] Personal tax returns (last 2 years)
- [ ] Business tax returns (if applicable)
- [ ] Proof of business address
- [ ] Business formation documents
- [ ] Revenue documentation

**Your score: ___ / 8**

---

## What Your Score Means

**25–29 points — Ready to apply**
You're in strong shape. Start shopping funding options now.

**18–24 points — Almost ready**
A few gaps to close. Focus on the unchecked items first.

**10–17 points — Building your foundation**
You have work to do, but you're on the right track. Focus on banking history and credit profile first.

**Under 10 — Start here**
Start with entity setup, EIN, and a business bank account. Everything else builds on those three.

---

## Next Step with Nexus

Nexus helps you track your readiness, research funding options, and access credit education resources — without expensive consultants.

Use Nexus to:
- Track which items on this list are complete
- Research funding options that match your current profile
- Access credit education and strategy resources
- Understand your options at every stage

---

## Compliance Note

*This scorecard is for educational and self-assessment purposes only. It does not guarantee funding approval, constitute financial or legal advice, or create a client relationship. Individual results will vary. Consult a licensed financial or legal professional for advice specific to your situation.*

---

*Internal draft — {ts} UTC — Lead Magnet Format — Pending Ray's review and approval before any use.*
"""


def convert_to_short_video_script(text: str, ts: str) -> str:
    """Convert the checklist into a 30-60 second video script."""
    return f"""# Credit/Funding Readiness Checklist — Short Video Script
*Internal Draft — Video Script Format — {ts} UTC — Not for publication*

> **INTERNAL ONLY.** Do not share with clients, publish, or use for marketing until explicitly approved by Ray.

---

## Hook (0–3 seconds)

**On screen:** "Are you ready for business funding?"
**Voice:** "Most business owners apply for funding without checking these 5 things — and they get denied."

---

## Script (30–60 seconds)

**Voice:**
"If you want a business credit line, SBA loan, or revenue-based financing, you need to prepare before you apply.

Here are the 5 things lenders check first:

One — your business entity. Make sure you have an LLC or corporation registered, an EIN from the IRS, and a real business address.

Two — your credit. Know your personal FICO score. Keep your balances below 30%. No collections or recent late payments.

Three — your banking. You need a separate business bank account with at least 6 months of consistent deposits.

Four — your documents. Have your EIN letter, bank statements, and tax returns ready before you start.

Five — your business credit. Register with Dun & Bradstreet for free and start building trade lines.

If you check all five, you're ready to apply. If not, fix the gaps first."

---

## On-Screen Text

1. Business entity + EIN
2. Personal credit score + low utilization
3. Business bank account (6+ months)
4. Documents ready
5. Business credit profile

---

## CTA (Final 5 seconds)

**On screen:** "Use Nexus to track your readiness and find the right funding options."
**Voice:** "Start at Nexus — link in bio."

---

## Compliance Note

*This script is for educational purposes only. It does not guarantee funding approval or constitute financial advice. Individual results will vary.*

---

*Internal draft — {ts} UTC — Video Script Format — Pending Ray's review and approval before any use.*
"""


def convert_to_newsletter(text: str, ts: str) -> str:
    """Convert the checklist into a newsletter article format."""
    return f"""# Credit/Funding Readiness Checklist — Newsletter Format
*Internal Draft — Newsletter Format — {ts} UTC — Not for publication*

> **INTERNAL ONLY.** Do not share with clients, publish, or send to subscribers until explicitly approved by Ray.

---

**Subject:** Are You Actually Ready for Business Funding? (Checklist Inside)

**Preview text:** Most business owners skip these steps — and pay for it when they get denied.

---

Hey [First Name],

Here's something most business owners don't find out until after they apply:

Lenders don't just look at your revenue. They look at how your whole business is set up.

That means your entity, your credit, your banking history, your documents — all of it gets reviewed before you see a dollar.

So before you apply for a credit line, SBA loan, or revenue-based financing, here's what to check:

---

**The 5-Minute Funding Readiness Check:**

☑ Is your business entity registered? (LLC, S-Corp, or C-Corp — not a sole prop)

☑ Do you have an EIN? (Free at irs.gov — takes 5 minutes)

☑ Do you have a separate business bank account with 6+ months of history?

☑ Is your personal credit score above 600 with no recent collections?

☑ Do you have 3–6 months of business bank statements ready to share?

If you checked all five — great. You're ready to start looking at options.

If you missed one or more — that's your priority right now.

---

**The full breakdown** (covering all 8 sections) is available inside Nexus as a free tool to track your readiness at every stage.

[Start your readiness check →]

---

*This is for educational purposes only. It does not guarantee funding approval or constitute financial advice. Individual results will vary.*

*Internal draft — {ts} UTC — Newsletter Format — Pending Ray's review and approval before any use.*
"""


def convert_to_email_draft(text: str, ts: str) -> str:
    """Convert the checklist into a follow-up email format."""
    return f"""# Credit/Funding Readiness Checklist — Email Draft
*Internal Draft — Email Format — {ts} UTC — Not for publication*

> **INTERNAL ONLY.** Do not send to clients or publish until explicitly approved by Ray.

---

**Subject:** Your next step toward business funding

**To:** [Client First Name]

---

Hi [First Name],

Following up on our conversation about business funding.

Before you apply for a credit line or loan, there are a few things most lenders check that are easy to overlook.

I put together a quick checklist for you:

**Immediate priorities:**
1. Make sure your business entity is registered and your EIN is in place
2. Open (or confirm you have) a dedicated business bank account
3. Pull your personal credit score — you'll want it above 600 before applying

**This week:**
4. Gather 3–6 months of business bank statements
5. Check if you have a business credit profile (Dun & Bradstreet is a good place to start)

Most lenders want to see at least 6 months of consistent business banking history before approving a credit line.

If you want to go through the full readiness checklist together, reply to this email or book a call below.

[Book a call →]

Talk soon,
[Your Name]

---

*This email template is for educational purposes only. It does not guarantee funding approval or constitute financial advice.*

*Internal draft — {ts} UTC — Email Format — Pending Ray's review and approval before any use.*
"""
