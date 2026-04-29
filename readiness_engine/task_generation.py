"""
task_generation.py — Generate missing-information tasks from client readiness profiles.

Tasks are generated based on missing fields and incomplete sections.
Each task includes guidance content from guidance_generator.
"""
from __future__ import annotations

from typing import Any

from readiness_engine.guidance_generator import SAFETY_DISCLAIMER, get_guidance

TASK_PRIORITY_HIGH = "high"
TASK_PRIORITY_MEDIUM = "medium"
TASK_PRIORITY_LOW = "low"


def _task(
    category: str,
    task_type: str,
    task_title: str,
    task_description: str,
    priority: str,
    unlocks_feature: str | None = None,
    education_notes: str = "",
    execution_tools: list[str] | None = None,
) -> dict[str, Any]:
    guidance = get_guidance(task_type)
    return {
        "category": category,
        "task_type": task_type,
        "task_title": task_title,
        "task_description": task_description,
        "guidance_content": guidance,
        "execution_tools": execution_tools or guidance.get("optional_tools") or [],
        "education_notes": education_notes or guidance.get("notes") or "",
        "priority": priority,
        "unlocks_feature": unlocks_feature,
        "status": "pending",
    }


def generate_business_foundation_tasks(data: dict[str, Any]) -> list[dict[str, Any]]:
    tasks = []

    entity_type = str(data.get("entity_type") or "").strip()
    if not entity_type or entity_type.lower() in {"sole_proprietor", "sole proprietor", "unregistered", "none", ""}:
        tasks.append(_task(
            category="business_foundation",
            task_type="llc_formation",
            task_title="Form a Legal Business Entity",
            task_description=(
                "Registering your business as an LLC, corporation, or other legal entity may be "
                "required by lenders and grant programs. Filing directly with your state is the "
                "commonly low-cost path."
            ),
            priority=TASK_PRIORITY_HIGH,
            unlocks_feature="funding_recommendations",
        ))

    ein_status = str(data.get("ein_status") or "").strip().lower()
    if ein_status not in {"active", "issued"}:
        tasks.append(_task(
            category="business_foundation",
            task_type="ein_setup",
            task_title="Obtain an EIN (Employer Identification Number)",
            task_description=(
                "An EIN is free to obtain from the IRS and is commonly required for business "
                "bank accounts, credit applications, and grants."
            ),
            priority=TASK_PRIORITY_HIGH,
            unlocks_feature="funding_recommendations",
        ))

    email_status = str(data.get("business_email_domain_status") or "").strip().lower()
    if email_status not in {"active", "verified"}:
        tasks.append(_task(
            category="business_foundation",
            task_type="business_email_domain_setup",
            task_title="Set Up a Professional Business Email Domain",
            task_description=(
                "A business email address on your own domain (e.g., name@yourbusiness.com) is "
                "commonly reviewed by lenders and grant evaluators as a legitimacy signal."
            ),
            priority=TASK_PRIORITY_MEDIUM,
        ))

    website_status = str(data.get("website_status") or "").strip().lower()
    if website_status not in {"active", "live"}:
        tasks.append(_task(
            category="business_foundation",
            task_type="website_setup",
            task_title="Set Up a Business Website",
            task_description=(
                "A basic business website is commonly reviewed by lenders and grant evaluators. "
                "A simple one-page site may be sufficient."
            ),
            priority=TASK_PRIORITY_MEDIUM,
        ))

    bank_status = str(data.get("business_bank_account_status") or "").strip().lower()
    if bank_status not in {"active", "open", "verified"}:
        tasks.append(_task(
            category="business_foundation",
            task_type="business_bank_account_setup",
            task_title="Open a Dedicated Business Bank Account",
            task_description=(
                "A dedicated business bank account separates personal and business finances and "
                "is commonly required by lenders and grant programs."
            ),
            priority=TASK_PRIORITY_HIGH,
            unlocks_feature="funding_recommendations",
        ))

    return tasks


def generate_credit_profile_tasks(data: dict[str, Any]) -> list[dict[str, Any]]:
    tasks = []

    if not data.get("credit_report_uploaded"):
        tasks.append(_task(
            category="credit_profile",
            task_type="credit_report_upload",
            task_title="Upload Your Credit Report",
            task_description=(
                "Uploading your credit report helps Nexus provide more accurate readiness assessments. "
                "Free reports are available at AnnualCreditReport.com."
            ),
            priority=TASK_PRIORITY_HIGH,
            unlocks_feature="funding_recommendations",
        ))

    neg = data.get("negative_items_count")
    try:
        neg_count = int(float(neg)) if neg is not None else 0
    except Exception:
        neg_count = 0
    if neg_count > 0:
        tasks.append(_task(
            category="credit_profile",
            task_type="credit_dispute",
            task_title="Review and Dispute Credit Report Errors",
            task_description=(
                "Your profile indicates potential negative items. Reviewing your report for "
                "inaccuracies and disputing errors through the credit bureaus is a commonly "
                "recommended step. Results vary and are not guaranteed."
            ),
            priority=TASK_PRIORITY_MEDIUM,
            education_notes=(
                "Nexus may generate educational dispute letter drafts as reference documents. "
                "Results are determined by the credit bureaus, not Nexus."
            ),
        ))

    duns_status = str(data.get("duns_status") or "").strip().lower()
    if duns_status not in {"active", "issued"}:
        tasks.append(_task(
            category="credit_profile",
            task_type="duns_setup",
            task_title="Register for a DUNS Number",
            task_description=(
                "A DUNS number establishes your business credit identity with Dun & Bradstreet "
                "and is commonly used by lenders and grant programs. Registration is free."
            ),
            priority=TASK_PRIORITY_MEDIUM,
            unlocks_feature="funding_recommendations",
        ))

    return tasks


def generate_banking_tasks(data: dict[str, Any]) -> list[dict[str, Any]]:
    tasks = []
    if not data.get("current_business_bank"):
        tasks.append(_task(
            category="banking_setup",
            task_type="business_bank_account_setup",
            task_title="Add Your Business Banking Information",
            task_description=(
                "Enter your current business bank details so Nexus can include banking "
                "history in your readiness assessment."
            ),
            priority=TASK_PRIORITY_HIGH,
            unlocks_feature="funding_recommendations",
        ))
    return tasks


def generate_grant_tasks(data: dict[str, Any]) -> list[dict[str, Any]]:
    tasks = []
    if not data.get("grant_documents_uploaded"):
        tasks.append(_task(
            category="grant_eligibility",
            task_type="grant_document_upload",
            task_title="Upload Grant Eligibility Documents",
            task_description=(
                "Grant applications commonly require formation certificates, EIN confirmation, "
                "and financial statements. Uploading these in advance may help when applying."
            ),
            priority=TASK_PRIORITY_LOW,
            unlocks_feature="grant_matching",
        ))
    return tasks


def generate_trading_tasks(data: dict[str, Any]) -> list[dict[str, Any]]:
    tasks = []

    if not data.get("disclaimer_accepted"):
        tasks.append(_task(
            category="trading_eligibility",
            task_type="trading_disclaimer",
            task_title="Review and Accept the Trading Disclaimer",
            task_description=(
                "Accept the Nexus trading disclaimer to confirm you understand the risks "
                "involved. This step is required before accessing trading tools."
            ),
            priority=TASK_PRIORITY_HIGH,
            unlocks_feature="trading_access",
        ))

    if not data.get("education_video_completed"):
        tasks.append(_task(
            category="trading_eligibility",
            task_type="trading_disclaimer",
            task_title="Complete the Trading Education Video",
            task_description=(
                "Watch the required trading education video to understand basic trading concepts "
                "and risk management. This step is required before accessing trading tools."
            ),
            priority=TASK_PRIORITY_HIGH,
            unlocks_feature="trading_access",
        ))

    if not data.get("paper_trading_completed"):
        tasks.append(_task(
            category="trading_eligibility",
            task_type="paper_trading_setup",
            task_title="Complete Paper Trading Practice",
            task_description=(
                "Complete at least one paper trading session (simulated trading without real capital) "
                "before accessing live trading tools."
            ),
            priority=TASK_PRIORITY_HIGH,
            unlocks_feature="trading_access",
        ))

    return tasks


def generate_all_tasks(
    foundation: dict[str, Any],
    credit: dict[str, Any],
    banking: dict[str, Any],
    grants: dict[str, Any],
    trading: dict[str, Any],
) -> list[dict[str, Any]]:
    tasks = (
        generate_business_foundation_tasks(foundation)
        + generate_credit_profile_tasks(credit)
        + generate_banking_tasks(banking)
        + generate_grant_tasks(grants)
        + generate_trading_tasks(trading)
    )
    for i, task in enumerate(tasks):
        task["sort_order"] = i
    return tasks


def get_next_best_action(tasks: list[dict[str, Any]]) -> dict[str, Any] | None:
    priority_order = {TASK_PRIORITY_HIGH: 0, TASK_PRIORITY_MEDIUM: 1, TASK_PRIORITY_LOW: 2}
    pending = [t for t in tasks if t.get("status") == "pending"]
    if not pending:
        return None
    return min(pending, key=lambda t: (priority_order.get(t.get("priority", "low"), 3), t.get("sort_order", 99)))
