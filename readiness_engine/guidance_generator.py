"""
guidance_generator.py — Safe, neutral educational guidance for each readiness task type.

Language requirements:
  - Use "may help", "commonly used", "educational guidance" framing.
  - Never guarantee credit repair, approval, funding, grants, or trading profits.
  - No required providers. No affiliate bias.
  - Free/low-cost path listed where applicable.
  - Convenience/paid path listed as optional where applicable.
"""
from __future__ import annotations

from typing import Any

SAFETY_DISCLAIMER = (
    "This information is provided for educational purposes only. "
    "Nexus does not guarantee credit repair, credit approval, funding approval, "
    "grant awards, or trading profits. Results vary. All decisions are made by "
    "lenders, grantors, or brokers, not by Nexus."
)


def _guidance(
    why: str,
    free_path: str,
    paid_path: str | None,
    tools: list[str] | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    return {
        "why_it_matters": why,
        "free_low_cost_path": free_path,
        "convenience_paid_path": paid_path or "Not required.",
        "optional_tools": tools or [],
        "notes": notes or "",
        "disclaimer": SAFETY_DISCLAIMER,
    }


_GUIDANCE_MAP: dict[str, dict[str, Any]] = {
    "llc_formation": _guidance(
        why=(
            "Forming an LLC or other legal entity separates personal and business liability, "
            "establishes a legal identity for your business, and may be required by many lenders "
            "and grant programs. Entity type commonly affects which financial products may be available."
        ),
        free_path=(
            "File directly with your state's Secretary of State or Corporation Commission website. "
            "Most states charge $50–$200 in filing fees. Search '[your state] LLC filing' to find "
            "the official state portal. The IRS website provides free EIN registration after formation."
        ),
        paid_path=(
            "Optional formation services such as Bizee, ZenBusiness, or Northwest Registered Agent "
            "may assist with filing paperwork for an additional fee. These are convenience options — "
            "filing directly with the state is equally valid and commonly lower cost."
        ),
        tools=["Secretary of State website (your state)", "IRS.gov (EIN registration)"],
        notes="Nexus does not endorse any specific formation service. Formation does not guarantee lender approval.",
    ),

    "ein_setup": _guidance(
        why=(
            "An Employer Identification Number (EIN) is issued by the IRS and commonly required "
            "to open a business bank account, apply for business credit, and complete grant applications. "
            "It is free to obtain directly from the IRS."
        ),
        free_path=(
            "Apply for free at IRS.gov using the online EIN application. The process typically takes "
            "10–15 minutes and an EIN is issued immediately upon approval. "
            "Visit IRS.gov and search 'Apply for an EIN online'."
        ),
        paid_path=(
            "Some business formation services include EIN registration as part of a paid package. "
            "This is optional — direct IRS registration is free and equally valid."
        ),
        tools=["IRS.gov EIN Assistant"],
    ),

    "credit_report_upload": _guidance(
        why=(
            "Uploading your credit report allows Nexus to provide more accurate readiness assessments "
            "and may help identify areas that commonly affect lending decisions. "
            "Credit reports are one of many factors lenders may review."
        ),
        free_path=(
            "Obtain your free annual credit reports at AnnualCreditReport.com, the official "
            "federally authorized source. You may request reports from Equifax, Experian, and TransUnion. "
            "Download as PDF and upload to your Nexus profile."
        ),
        paid_path=(
            "Optional paid credit monitoring services such as SmartCredit, myFICO, or Credit Karma "
            "may provide more frequent updates and additional detail. These are convenience options."
        ),
        tools=["AnnualCreditReport.com (free)", "SmartCredit (optional paid)"],
        notes="Nexus stores only what you choose to upload. Credit scores shown are estimates only.",
    ),

    "credit_dispute": _guidance(
        why=(
            "Reviewing your credit report for inaccuracies is a commonly recommended step. "
            "Disputing errors with credit bureaus may help over time — results vary and are not guaranteed. "
            "The dispute process is governed by the Fair Credit Reporting Act (FCRA)."
        ),
        free_path=(
            "You may dispute errors directly with each credit bureau (Equifax, Experian, TransUnion) "
            "at no cost through their online portals or by mail. "
            "The Consumer Financial Protection Bureau (CFPB) provides free dispute guidance at consumerfinance.gov."
        ),
        paid_path=(
            "Nexus may generate educational dispute letter drafts as reference documents. "
            "Optional mailing services such as Docupost may be used to send letters. "
            "These are tools only — Nexus does not guarantee dispute outcomes. "
            "Results are determined by the credit bureaus."
        ),
        tools=["CFPB (consumerfinance.gov)", "Equifax.com disputes", "Experian.com disputes", "TransUnion.com disputes"],
        notes=(
            "Nexus dispute letter drafts are educational reference documents only. "
            "They do not guarantee removal of any item. Credit repair results vary."
        ),
    ),

    "business_bank_account_setup": _guidance(
        why=(
            "A dedicated business bank account is commonly required by lenders and grant programs. "
            "It separates personal and business finances and may support your banking history, "
            "which lenders often review as part of cash flow analysis."
        ),
        free_path=(
            "Many local credit unions and community banks offer free or low-fee business checking accounts. "
            "Contact institutions in your area directly to compare options. "
            "NCUA.gov has a credit union locator."
        ),
        paid_path=(
            "National banks and online business banking platforms such as Relay, Mercury, or Bluevine "
            "offer business accounts with varying fee structures. These are convenience options — "
            "a local credit union account is equally valid."
        ),
        tools=["NCUA.gov credit union locator", "FDIC.gov bank locator"],
        notes="Nexus does not connect to or access bank accounts. Only manual status and proof fields are stored.",
    ),

    "duns_setup": _guidance(
        why=(
            "A DUNS number is a unique business identifier issued by Dun & Bradstreet. "
            "It is commonly used by lenders and grant programs to look up your Paydex business credit score. "
            "Establishing a DUNS number and reporting business tradelines may support business credit building over time."
        ),
        free_path=(
            "A DUNS number can be registered for free at dnb.com/duns-number. "
            "The free process may take several business days. "
            "Paying vendor invoices on time is commonly associated with a higher Paydex score."
        ),
        paid_path=(
            "Dun & Bradstreet offers expedited registration and monitoring services for a fee. "
            "These are optional convenience services."
        ),
        tools=["dnb.com/duns-number (free registration)"],
    ),

    "business_email_domain_setup": _guidance(
        why=(
            "A professional business email using your own domain (e.g., name@yourbusiness.com) "
            "is commonly required or preferred by lenders and grant applications. "
            "It may be reviewed as part of business legitimacy checks."
        ),
        free_path=(
            "Register a domain through a domain registrar (typically $10–$15/year). "
            "Many web hosting providers include free business email with a domain purchase. "
            "Google Workspace and Microsoft 365 offer paid business email options."
        ),
        paid_path=(
            "Paid services such as Google Workspace or Microsoft 365 provide hosted business email "
            "with additional collaboration features. These are optional upgrades."
        ),
        tools=["Namecheap, GoDaddy, or Google Domains (domain registration)"],
    ),

    "website_setup": _guidance(
        why=(
            "A business website is commonly reviewed by lenders and grant evaluators as evidence "
            "of an active, legitimate business. It does not need to be complex — "
            "a simple professional presence may be sufficient."
        ),
        free_path=(
            "Platforms such as Google Sites, Wix (free tier), or WordPress.com (free tier) "
            "allow basic website creation at no cost. A simple one-page site with your business "
            "name, services, and contact information is commonly sufficient."
        ),
        paid_path=(
            "Paid website builders such as Squarespace, Wix, or Webflow offer more customization. "
            "A custom domain (typically $10–$15/year) is recommended for a professional appearance."
        ),
        tools=["Google Sites (free)", "Wix (free tier)", "WordPress.com (free tier)"],
    ),

    "grant_document_upload": _guidance(
        why=(
            "Grant applications commonly require supporting documents such as formation certificates, "
            "EIN confirmation letters, financial statements, or proof of eligibility. "
            "Uploading these in advance may help when applying."
        ),
        free_path=(
            "Gather documents from their original sources: "
            "formation documents from your state's Secretary of State website, "
            "EIN confirmation from the IRS, bank statements from your business bank. "
            "Scan or download as PDFs."
        ),
        paid_path=None,
        tools=["State Secretary of State website", "IRS.gov (EIN records)"],
        notes=(
            "Nexus stores only what you choose to upload. "
            "Document requirements vary by grant program. "
            "Nexus does not guarantee grant approval."
        ),
    ),

    "trading_disclaimer": _guidance(
        why=(
            "Reviewing and accepting the trading disclaimer is required before accessing "
            "Nexus trading tools. This confirms you understand the risks involved in trading "
            "and that Nexus does not guarantee trading profits or investment returns."
        ),
        free_path="Review and accept the disclaimer in your Nexus trading profile.",
        paid_path=None,
        notes=(
            "Trading involves risk. Past performance does not guarantee future results. "
            "Nexus trading tools are for educational and informational purposes only."
        ),
    ),

    "paper_trading_setup": _guidance(
        why=(
            "Completing paper trading (simulated trading without real money) is a commonly "
            "recommended step before trading with real capital. It allows you to practice "
            "strategies without financial risk."
        ),
        free_path=(
            "Many brokers offer free paper trading platforms. "
            "TD Ameritrade's thinkorswim, Interactive Brokers, and TradeStation "
            "offer paper trading at no cost."
        ),
        paid_path=None,
        tools=["thinkorswim by TD Ameritrade (free)", "Interactive Brokers paper trading (free)"],
        notes=(
            "Paper trading results do not guarantee live trading performance. "
            "Nexus does not endorse any specific broker."
        ),
    ),
}


def get_guidance(task_type: str) -> dict[str, Any]:
    return _GUIDANCE_MAP.get(task_type, {
        "why_it_matters": "Complete this task to improve your readiness profile.",
        "free_low_cost_path": "See task description for details.",
        "convenience_paid_path": "Not required.",
        "optional_tools": [],
        "notes": "",
        "disclaimer": SAFETY_DISCLAIMER,
    })


def list_supported_task_types() -> list[str]:
    return list(_GUIDANCE_MAP.keys())
