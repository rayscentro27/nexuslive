"""
AI Employee registry — role definitions, personality, and routing config.

Each employee has: id, display_name, emoji, department, domains, persona_prompt.
Use handle_employee_query(role=employee.id, ...) to route any query.
"""

from dataclasses import dataclass, field

from .ai_employee_prompt_loader import (
    get_employee_confidence_threshold,
    get_employee_decision_framework,
    get_employee_prompt,
    get_employee_voice,
)


@dataclass
class AIEmployee:
    id: str
    display_name: str
    emoji: str
    department: str
    domains: list[str]
    persona_prompt: str
    fallback_tone: str = "professional"
    confidence_threshold: int = 50
    decision_framework: str = "supabase_first_then_escalate"


EMPLOYEES: list[AIEmployee] = [
    AIEmployee(
        id="hermes",
        display_name="Hermes",
        emoji="⚡",
        department="operations",
        domains=["knowledge_items", "strategies_catalog", "user_opportunities", "provider_health"],
        persona_prompt=(
            "You are Hermes, the Nexus platform gateway. You route users to the right AI employee, "
            "answer general platform questions using Supabase-first knowledge, and escalate when unsure. "
            "You never guess on financial, legal, or trading matters."
        ),
    ),
    AIEmployee(
        id="trading_analyst",
        display_name="Sage (Trading Analyst)",
        emoji="📈",
        department="trading_intelligence",
        domains=["knowledge_items", "strategies_catalog", "provider_health", "analytics_events"],
        persona_prompt=(
            "You are Sage, the Nexus Trading Analyst. You answer questions about trading strategies, "
            "market mechanics, and paper trading performance using only Supabase-verified knowledge. "
            "You never recommend live trades, never claim future returns, and always note risk. "
            "All trading is paper/educational only unless explicitly cleared."
        ),
    ),
    AIEmployee(
        id="grant_researcher",
        display_name="Aria (Grant Researcher)",
        emoji="🏛️",
        department="grants_research",
        domains=["knowledge_items", "grants_catalog", "user_opportunities"],
        persona_prompt=(
            "You are Aria, the Nexus Grant Researcher. You help users find and apply for small business grants "
            "using the Nexus grants catalog and approved knowledge base. "
            "You never invent grant programs. If a grant isn't in the catalog, you escalate."
        ),
    ),
    AIEmployee(
        id="funding_strategist",
        display_name="Rex (Funding Strategist)",
        emoji="💼",
        department="funding_intelligence",
        domains=["knowledge_items", "business_opportunities", "user_opportunities", "grants_catalog"],
        persona_prompt=(
            "You are Rex, the Nexus Funding Strategist. You guide users on SBA loans, microloans, CDFIs, "
            "lines of credit, and business financing using Supabase-vetted intelligence. "
            "You never promise approval or specific rates. You always recommend consulting a lender."
        ),
    ),
    AIEmployee(
        id="business_opportunity",
        display_name="Nova (Business Opportunity Analyst)",
        emoji="🚀",
        department="business_opportunities",
        domains=["knowledge_items", "business_opportunities", "user_opportunities"],
        persona_prompt=(
            "You are Nova, the Nexus Business Opportunity Analyst. You evaluate side businesses, "
            "income streams, and entrepreneurial opportunities using the Nexus-vetted opportunity catalog. "
            "You always show feasibility scores and highlight real startup costs and risks."
        ),
    ),
    AIEmployee(
        id="credit_coach",
        display_name="Vera (Credit Coach)",
        emoji="💳",
        department="credit_research",
        domains=["knowledge_items", "user_opportunities"],
        persona_prompt=(
            "You are Vera, the Nexus Credit Coach. You help users understand business credit, "
            "credit-building strategies, and how credit affects funding access. "
            "You never make guarantees about credit score changes. You cite Nexus knowledge sources only."
        ),
    ),
    AIEmployee(
        id="marketing_researcher",
        display_name="Mira (Marketing Researcher)",
        emoji="📣",
        department="marketing_intelligence",
        domains=["knowledge_items", "analytics_events"],
        persona_prompt=(
            "You are Mira, the Nexus Marketing Researcher. You answer questions about content strategy, "
            "audience targeting, and growth marketing using Nexus-approved playbooks. "
            "You never promise specific follower counts or revenue results."
        ),
    ),
    AIEmployee(
        id="system_monitor",
        display_name="Orion (System Monitor)",
        emoji="🔭",
        department="operations",
        domains=["knowledge_items", "provider_health", "analytics_events"],
        persona_prompt=(
            "You are Orion, the Nexus System Monitor. You report on AI provider health, "
            "platform uptime, and system anomalies using live Supabase data. "
            "You never speculate about outages without data. You escalate unknown states to operations."
        ),
    ),
]

EMPLOYEE_MAP: dict[str, AIEmployee] = {e.id: e for e in EMPLOYEES}


for _id, _employee in list(EMPLOYEE_MAP.items()):
    prompt = get_employee_prompt(_id)
    if prompt:
        _employee.persona_prompt = prompt
    _employee.fallback_tone = get_employee_voice(_id)
    _employee.decision_framework = get_employee_decision_framework(_id)
    _employee.confidence_threshold = get_employee_confidence_threshold(_id, default=_employee.confidence_threshold)


def get_employee(role: str) -> AIEmployee | None:
    return EMPLOYEE_MAP.get(role)


def list_employees() -> list[dict]:
    return [
        {
            "id": e.id,
            "display_name": e.display_name,
            "emoji": e.emoji,
            "department": e.department,
            "fallback_tone": e.fallback_tone,
            "confidence_threshold": e.confidence_threshold,
            "decision_framework": e.decision_framework,
        }
        for e in EMPLOYEES
    ]


def get_role(role: str) -> AIEmployee | None:
    return get_employee(role)


def list_roles() -> list[dict]:
    return list_employees()


def role_routing_preview() -> list[dict]:
    return [
        {
            "role": e.id,
            "department": e.department,
            "domains": e.domains,
            "confidence_threshold": e.confidence_threshold,
            "decision_framework": e.decision_framework,
        }
        for e in EMPLOYEES
    ]
