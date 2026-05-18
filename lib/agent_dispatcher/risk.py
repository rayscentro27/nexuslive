"""
Nexus Agent Dispatcher — Risk Assessment.

Classifies tasks by risk level based on keywords, intent, and content.
Hard blocks certain actions regardless of context.
"""
from __future__ import annotations

from enum import Enum
from typing import Any


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Patterns that trigger risk escalation
_CRITICAL_PATTERNS = frozenset({
    "live trading", "real money", "real-money", "production deploy", "drop table",
    "delete all", "service role key", "expose secret", "billing", "charge card",
    "execute trade", "buy order", "sell order", "production migration",
    "send to all users", "mass email", "unrestricted shell", "sudo rm",
})

_HIGH_PATTERNS = frozenset({
    "deploy", "production", "database migration", "alter table", "client message",
    "funding decision", "credit approval", "trading signal", "external send",
    "push to main", "force push", "stripe", "payment", "auth token",
    "personal data", "user data export", "admin override",
})

_MEDIUM_PATTERNS = frozenset({
    "code change", "modify file", "staging", "test deploy", "dashboard update",
    "insert into", "update table", "schedule job", "worker restart",
    "config change", "grant access",
})

# Hard-blocked actions — never allowed regardless of approval
_HARD_BLOCKS = frozenset({
    "live trading", "real money trading", "live execution", "real-money trading",
    "expose secrets", "expose service role key", "disable rls",
    "delete all knowledge", "mass approve blindly",
})


def assess_risk(prompt: str, task_type: str = "") -> dict[str, Any]:
    """
    Assess the risk level of a prompt/task.

    Returns:
        {
            "risk_level": str,
            "requires_approval": bool,
            "hard_blocked": bool,
            "block_reason": str | None,
            "risk_factors": list[str],
        }
    """
    text = (prompt or "").lower().strip()
    factors: list[str] = []
    hard_blocked = False
    block_reason: str | None = None

    # Check hard blocks first
    for pattern in _HARD_BLOCKS:
        if pattern in text:
            hard_blocked = True
            block_reason = f"Hard-blocked action detected: '{pattern}'"
            break

    # Scan risk patterns
    level = RiskLevel.LOW
    for pattern in _CRITICAL_PATTERNS:
        if pattern in text:
            level = RiskLevel.CRITICAL
            factors.append(f"critical_pattern:{pattern}")

    if level != RiskLevel.CRITICAL:
        for pattern in _HIGH_PATTERNS:
            if pattern in text:
                if level.value != "critical":
                    level = RiskLevel.HIGH
                factors.append(f"high_pattern:{pattern}")

    if level not in {RiskLevel.CRITICAL, RiskLevel.HIGH}:
        for pattern in _MEDIUM_PATTERNS:
            if pattern in text:
                if level == RiskLevel.LOW:
                    level = RiskLevel.MEDIUM
                factors.append(f"medium_pattern:{pattern}")

    # Task type overrides
    high_risk_task_types = {"deploy", "migration", "billing", "external_comms", "trading_execution"}
    if task_type in high_risk_task_types and level == RiskLevel.LOW:
        level = RiskLevel.MEDIUM
        factors.append(f"task_type_escalation:{task_type}")

    requires_approval = level in {RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL} or hard_blocked

    return {
        "risk_level": level.value,
        "requires_approval": requires_approval,
        "hard_blocked": hard_blocked,
        "block_reason": block_reason,
        "risk_factors": factors[:10],
    }
