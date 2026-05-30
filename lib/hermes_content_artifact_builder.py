"""
hermes_content_artifact_builder.py
=====================================
Builds reviewable internal content draft artifacts for Ray.

All drafts are internal-only until Ray explicitly approves publishing.
No content is sent to clients, published, or monetized by this module.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_ROOT = Path(__file__).resolve().parent.parent
_CONTENT_DIR = _ROOT / "docs" / "reports" / "content"

_CHECKLIST_SLUG = "credit_funding_readiness_checklist"
_CHECKLIST_ACTION_ID = "act_aa99698ef8"
_CHECKLIST_TITLE = "Credit/Funding Readiness Checklist"


# ── Path helpers ─────────────────────────────────────────────────────────────

def build_content_artifact_path(topic: str, timestamp: str) -> Path:
    safe = topic.lower().replace(" ", "_").replace("/", "_")[:50]
    return _CONTENT_DIR / f"{safe}_draft_{timestamp}.md"


def _find_existing_checklist_draft() -> Optional[Path]:
    if not _CONTENT_DIR.exists():
        return None
    drafts = sorted(_CONTENT_DIR.glob(f"{_CHECKLIST_SLUG}_draft_*.md"), reverse=True)
    return drafts[0] if drafts else None


# ── Action lookup ─────────────────────────────────────────────────────────────

def find_best_content_action() -> Optional[dict]:
    try:
        from lib.hermes_action_queue import get_unique_open_actions, _is_meta_action
        for a in get_unique_open_actions():
            if _is_meta_action(a):
                continue
            t = (a.title or "").lower()
            if any(k in t for k in ["checklist", "credit", "funding", "lead magnet", "template", "newsletter"]):
                return {
                    "action_id": a.action_id,
                    "title": a.title,
                    "scout": a.assigned_scout,
                    "status": a.status,
                }
    except Exception:
        pass
    return None


# ── Main draft creation ───────────────────────────────────────────────────────

def create_credit_funding_readiness_checklist_draft(new_version: bool = False) -> dict:
    """
    Write the Credit/Funding Readiness Checklist draft to disk.
    Returns dict: created, path (relative str), action_id, is_duplicate.
    Does not publish. Does not spend money. Internal draft only.
    """
    existing = _find_existing_checklist_draft()
    if existing and not new_version:
        return {
            "created": False,
            "path": str(existing.relative_to(_ROOT)),
            "action_id": _CHECKLIST_ACTION_ID,
            "is_duplicate": True,
        }

    _CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = build_content_artifact_path(_CHECKLIST_SLUG, ts)
    path.write_text(_build_checklist_markdown(ts))

    meta_path = _CONTENT_DIR / f"{_CHECKLIST_SLUG}_draft_{ts}.json"
    meta_path.write_text(json.dumps({
        "title": _CHECKLIST_TITLE,
        "draft_version": ts,
        "action_id": _CHECKLIST_ACTION_ID,
        "status": "internal_draft",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "requires_approval_before": ["publishing", "selling", "client use", "website", "email"],
    }, indent=2))

    _register_artifact(path, ts)
    _update_action(path)
    _log_decision(path)

    return {
        "created": True,
        "path": str(path.relative_to(_ROOT)),
        "action_id": _CHECKLIST_ACTION_ID,
        "is_duplicate": False,
    }


def create_content_draft_from_action(action_id: str) -> dict:
    if action_id in (_CHECKLIST_ACTION_ID, ""):
        return create_credit_funding_readiness_checklist_draft()
    return {"created": False, "error": f"No draft builder for action {action_id}"}


# ── Side-effects ──────────────────────────────────────────────────────────────

def _register_artifact(path: Path, ts: str) -> None:
    try:
        from lib.hermes_artifact_memory import register_artifact
        register_artifact(
            artifact_type="content_draft",
            path=path,
            run_id=ts,
            summary=f"Internal first draft — {_CHECKLIST_TITLE}. Review before publishing.",
        )
    except Exception:
        pass


def _update_action(path: Path) -> None:
    try:
        from lib.hermes_action_queue import update_action_status
        update_action_status(
            _CHECKLIST_ACTION_ID,
            status="completed_with_artifact",
            artifact_outputs=[str(path.relative_to(_ROOT))],
            next_step="Ray review — approve before publishing",
        )
    except Exception:
        pass


def _log_decision(path: Path) -> None:
    try:
        from lib.hermes_decision_log import log_decision
        log_decision(
            question_or_trigger="Ray requested: create first draft for Credit/Funding Readiness Checklist",
            decision="Created internal draft Markdown artifact for Ray review",
            why_selected="Fastest reviewable revenue asset — can become lead magnet, paid template, or newsletter opt-in",
            artifact_paths=[str(path.relative_to(_ROOT))],
            goal_alignment="First product toward Nexus revenue goal",
            risk_level="low",
            autonomous_allowed=True,
            requires_ray_approval=False,
            action_created=_CHECKLIST_ACTION_ID,
            result_status="completed_with_artifact",
        )
    except Exception:
        pass


# ── Response formatting ───────────────────────────────────────────────────────

def format_content_created_response(result: dict) -> str:
    path = result.get("path", "")
    action_id = result.get("action_id", "")
    decision_log = "docs/reports/decisions/hermes_decision_log.jsonl"

    if result.get("is_duplicate"):
        return (
            f"I already created the draft. Here is the latest artifact path:\n\n"
            f"Draft: {path}\n"
            f"Action: {action_id}\n\n"
            f"Status: Internal draft only.\n"
            f"Approval required before publishing, selling, or sharing with clients.\n\n"
            f"To create a new version, say: create a new version of the checklist draft."
        )

    if not result.get("created"):
        return f"Could not create draft: {result.get('error', 'unknown error')}"

    return (
        "CONTENT DRAFT CREATED\n\n"
        "I created the first internal draft for review.\n\n"
        "Draft:\n"
        f"{_CHECKLIST_TITLE}\n\n"
        "Why this matters:\n"
        "This is our fastest reviewable revenue asset. It can become a lead magnet, "
        "paid template, newsletter opt-in, or funding-readiness offer.\n\n"
        "Status:\n"
        "Internal draft only.\n\n"
        "Approval:\n"
        "No approval needed for internal draft.\n"
        "Approval required before publishing, selling, emailing clients, or adding to the website.\n\n"
        f"Evidence:\n"
        f"- Draft: {path}\n"
        f"- Action: {action_id}\n"
        f"- Decision log: {decision_log}\n\n"
        "Next:\n"
        "Review the draft and tell me what to improve."
    )


# ── Draft content ─────────────────────────────────────────────────────────────

def _build_checklist_markdown(ts: str) -> str:
    return f"""# Credit/Funding Readiness Checklist
*Internal Draft — {ts} UTC — Not for publication*

> **INTERNAL ONLY.** This draft is for Ray's review. Do not share with clients, publish, or use for marketing until explicitly approved.

---

## Who This Checklist Is For

Business owners who want to apply for business funding — credit lines, SBA loans, revenue-based financing, or business credit cards — and need to know what to prepare before they apply.

---

## 1. Business Setup Readiness

- [ ] **Business entity formed** — LLC, S-Corp, or C-Corp registered with your state
- [ ] **EIN obtained** — Employer Identification Number from the IRS (free at irs.gov)
- [ ] **Business address** — physical or registered agent address (not a P.O. box for most lenders)
- [ ] **Business phone number** — separate from personal; listed consistently
- [ ] **Business email** — professional address matching your domain
- [ ] **Website** — basic site showing your business is active
- [ ] **NAICS code** — industry classification code; know yours before applying
- [ ] **Business description** — clear, one-sentence description of what your business does

---

## 2. Credit Profile Readiness

### Personal Credit
- [ ] **Know your score** — check current FICO 8 score (FICO SBSS matters for SBA)
- [ ] **Credit utilization** — revolving balances below 30% of limits
- [ ] **Derogatory items** — review for collections, charge-offs, late payments
- [ ] **Payment history** — 12+ months of on-time payments strengthens your profile
- [ ] **Credit mix** — both revolving and installment accounts help

### Business Credit
- [ ] **Business credit profile exists** — check Dun & Bradstreet, Experian Business, Equifax Business
- [ ] **DUNS number** — register with D&B if you don't have one (free)
- [ ] **Trade lines** — at least 3–5 accounts reporting to business credit bureaus

---

## 3. Business Banking Readiness

- [ ] **Separate business bank account** — never use personal accounts for business
- [ ] **Account age** — most lenders want 6–12 months of history
- [ ] **Regular deposits** — consistent revenue activity in the account
- [ ] **No overdrafts** — negative balances are a red flag
- [ ] **Bookkeeping current** — income and expenses tracked (QuickBooks, Wave, etc.)

---

## 4. Documentation Readiness

Have these ready before you apply:

- [ ] **Government-issued ID** — driver's license or passport
- [ ] **EIN letter** — IRS confirmation (CP575 or 147C)
- [ ] **3–6 months business bank statements**
- [ ] **Personal tax returns** — last 2 years
- [ ] **Business tax returns** — if applicable, last 1–2 years
- [ ] **Proof of business address** — utility bill, lease, or bank statement
- [ ] **Business formation documents** — articles of incorporation or LLC operating agreement
- [ ] **Revenue documentation** — invoices, contracts, or payment processor statements if needed

---

## 5. Funding Red Flags to Fix First

These will hurt your application. Address them before applying.

- ❌ **Inconsistent business info** — name, address, or phone differs across IRS, state, and bank records
- ❌ **Personal credit below 600** — significantly limits your options
- ❌ **No business banking history** — most lenders require 3–12 months of statements
- ❌ **Unclear revenue** — lenders verify deposits, not projections
- ❌ **Business under 6 months old** — many programs require 6–24 months in business
- ❌ **Open tax liens or judgments** — must be addressed before most funding

---

## 6. What to Fix First (Priority Order)

1. **Get the entity and EIN** — nothing else works without these
2. **Open a business bank account** — start building history immediately
3. **Clean up personal credit** — dispute errors, reduce utilization
4. **Establish business credit** — vendor accounts, net-30 suppliers, secured business card
5. **Track 6 months of revenue** — consistent deposits build your profile
6. **Gather your documents** — EIN letter, statements, returns

---

## 7. Nexus Next Step

Use Nexus to organize your funding readiness, business setup, credit education, and opportunity research.

Nexus can help you:
- Track which readiness steps are complete
- Research funding options matching your profile
- Access credit education resources
- Understand your options without expensive consultants

---

## Compliance Note

*This checklist is for educational purposes only. It does not guarantee funding approval, constitute financial or legal advice, or create a client relationship. Individual results will vary. Consult a licensed financial or legal professional for advice specific to your situation.*

---

*Internal draft — {ts} UTC — Pending Ray's review and approval before any use.*
"""
