"""
prompt_builder.py — Render AI employee prompts for Nexus workers.

Composes a final prompt from three layers:
  1. Shared compliance header  (skills/roles/_base.md)
  2. Role-specific shell       (skills/roles/{role}.md)
  3. User context              (from Supabase or inline dict)
  4. Task                      (caller-supplied string)

Only non-empty context fields are injected — no token waste on blank sections.

Usage:
    from lib.prompt_builder import PromptBuilder

    # Simple build — no user context:
    prompt = PromptBuilder("credit_analyst").build(
        task="The user has a 640 personal score and no business credit. Analyze."
    )

    # With Supabase user context:
    prompt = PromptBuilder("funding_strategist").build(
        task="Design a 90-day funding roadmap.",
        user_id="uuid-here",
    )

    # With inline user data (bypass Supabase):
    prompt = PromptBuilder("ceo").build(
        task="Assess and assign next step.",
        user_data={
            "name": "Marcus",
            "plan": "pro",
            "stage": "Fundable",
            "goal": "Access $50K business credit",
        }
    )

    # From a Supabase job row:
    prompt = PromptBuilder.from_job(job_row).build(task=job_row["description"])
"""
from __future__ import annotations

import json
import logging
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

# Allow `python3 lib/prompt_builder.py` to run from any cwd
_LIB_PARENT = Path(__file__).resolve().parent.parent
if str(_LIB_PARENT) not in sys.path:
    sys.path.insert(0, str(_LIB_PARENT))

from lib.env_loader import load_nexus_env

load_nexus_env()

logger = logging.getLogger("PromptBuilder")

_ROOT        = Path(__file__).resolve().parent.parent          # nexus-ai/
_ROLES_DIR   = _ROOT / "skills" / "roles"
_BASE_FILE   = _ROLES_DIR / "_base.md"
_DEFAULT_ROLE = "default"

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY", "")

# ── Plan → Stage mapping ───────────────────────────────────────────────────────
_PLAN_STAGE: dict[str, str] = {
    "free":   "Building Foundation",
    "pro":    "Fundable",
    "elite":  "Funded / Scaling",
}

# ── Available role names (for validation) ─────────────────────────────────────
KNOWN_ROLES = {
    "credit_analyst",
    "funding_strategist",
    "content_creator",
    "ad_copy_agent",
    "compliance_reviewer",
    "ceo",
}


# ── Supabase helpers ───────────────────────────────────────────────────────────

def _sb_headers() -> dict:
    return {
        "apikey":        SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type":  "application/json",
    }


def _sb_get(path: str, timeout: int = 8) -> list:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return []
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    req = urllib.request.Request(url, headers=_sb_headers())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read()) or []
    except Exception as e:
        logger.debug("Supabase fetch failed (%s): %s", path, e)
        return []


# ── Role file loader ───────────────────────────────────────────────────────────

def _load_role(role: str) -> str:
    path = _ROLES_DIR / f"{role}.md"
    if not path.exists():
        logger.warning("Role file not found for '%s', using default", role)
        path = _ROLES_DIR / f"{_DEFAULT_ROLE}.md"
    return path.read_text().strip()


def _load_base() -> str:
    if _BASE_FILE.exists():
        return _BASE_FILE.read_text().strip()
    return "You are an AI employee at Nexus. Never guarantee outcomes. Educate first."


# ── User context builder ───────────────────────────────────────────────────────

def _derive_stage(plan: str, events: list) -> str:
    if plan in _PLAN_STAGE:
        return _PLAN_STAGE[plan]
    # Infer from recent events if plan is unknown
    event_types = {(e.get("event_type") or "").lower() for e in events}
    if "funding_approved" in event_types:
        return "Funded"
    if "credit_reviewed" in event_types or "business_formed" in event_types:
        return "Fundable"
    return "Unfunded"


def _render_context(data: dict) -> str:
    """Convert a user data dict into a compact context block. Skips empty fields."""
    lines = []

    mappings = [
        ("name",           "Name"),
        ("email",          "Email"),
        ("plan",           "Subscription Plan"),
        ("stage",          "Current Stage"),
        ("goal",           "Current Goal"),
        ("credit_score",   "Credit Score"),
        ("business_name",  "Business Name"),
        ("known_issues",   "Known Issues"),
        ("recent_events",  "Recent Activity"),
        ("pending_tasks",  "Open Tasks"),
        ("notes",          "Notes"),
    ]

    for key, label in mappings:
        value = data.get(key)
        if not value:
            continue
        if isinstance(value, list):
            if not value:
                continue
            lines.append(f"{label}:")
            for item in value[:5]:  # cap at 5 items to control tokens
                lines.append(f"  - {item}")
        else:
            lines.append(f"{label}: {value}")

    return "\n".join(lines) if lines else ""


# ── Main class ─────────────────────────────────────────────────────────────────

class PromptBuilder:
    """
    Builds a complete AI employee prompt for a given role and user context.

    Args:
        role: One of the known roles or any string (falls back to default.md).
    """

    def __init__(self, role: str):
        self.role = role.lower().strip()
        self._base   = _load_base()
        self._shell  = _load_role(self.role)

    # ── Public API ─────────────────────────────────────────────────────────────

    def build(
        self,
        task: str,
        user_id:   Optional[str]  = None,
        user_data: Optional[dict] = None,
        extra:     Optional[str]  = None,
    ) -> str:
        """
        Compose the final prompt.

        Args:
            task:      The specific task or question for this AI employee.
            user_id:   Supabase user UUID — triggers a live context fetch.
            user_data: Inline dict — used directly (overrides Supabase fetch).
            extra:     Any additional context to append before the task.

        Returns:
            Fully composed prompt string, ready to send to any LLM.
        """
        # Resolve user context
        if user_data:
            context_data = user_data
        elif user_id:
            context_data = self.fetch_user_context(user_id)
        else:
            context_data = {}

        context_block = _render_context(context_data)

        # Compose sections
        parts = [self._base, "", self._shell]

        if context_block:
            parts += ["", "USER CONTEXT", "───────────", context_block]

        if extra:
            parts += ["", "ADDITIONAL CONTEXT", "──────────────────", extra.strip()]

        parts += ["", "TASK", "────", task.strip()]

        return "\n".join(parts)

    def fetch_user_context(self, user_id: str) -> dict:
        """
        Pull user context from Supabase.
        Returns a dict ready to pass to _render_context().
        Degrades gracefully if tables don't exist or Supabase is unreachable.
        """
        data: dict = {}

        # ── User profile ──────────────────────────────────────────────────────
        profiles = _sb_get(
            f"user_profiles?id=eq.{user_id}&select=full_name,email,subscription_plan&limit=1"
        )
        if profiles:
            p = profiles[0]
            data["name"]  = p.get("full_name") or ""
            data["email"] = p.get("email") or ""
            plan = (p.get("subscription_plan") or "free").lower()
            data["plan"]  = plan

        # ── Subscription ──────────────────────────────────────────────────────
        subs = _sb_get(
            f"user_subscriptions?user_id=eq.{user_id}&select=plan,status&limit=1"
        )
        if subs:
            s = subs[0]
            if not data.get("plan"):
                data["plan"] = (s.get("plan") or "free").lower()

        # ── Recent events ─────────────────────────────────────────────────────
        events = _sb_get(
            f"system_events"
            f"?payload->>client_id=eq.{user_id}"
            f"&select=event_type,created_at"
            f"&order=created_at.desc&limit=8"
        )
        if events:
            data["recent_events"] = [
                e.get("event_type", "unknown") for e in events
            ]

        # ── Pending tasks ─────────────────────────────────────────────────────
        tasks = _sb_get(
            f"tasks"
            f"?metadata->>client_id=eq.{user_id}"
            f"&status=in.(pending,in_progress)"
            f"&select=title&limit=5"
        )
        if tasks:
            data["pending_tasks"] = [t.get("title", "") for t in tasks if t.get("title")]

        # ── Derive stage ──────────────────────────────────────────────────────
        data["stage"] = _derive_stage(data.get("plan", "free"), events)

        return data

    def estimate_tokens(self, task: str, user_data: Optional[dict] = None) -> int:
        """Rough token estimate for the composed prompt (4 chars ≈ 1 token)."""
        prompt = self.build(task, user_data=user_data or {})
        return len(prompt) // 4

    # ── Classmethods ──────────────────────────────────────────────────────────

    @classmethod
    def from_job(cls, job: dict) -> "PromptBuilder":
        """
        Instantiate from a Supabase job_queue or workflow_outputs row.

        Expected job keys: role, payload (dict with user_id, user_data, etc.)
        """
        role = (job.get("role") or job.get("agent_role") or _DEFAULT_ROLE).lower()
        return cls(role)

    @classmethod
    def available_roles(cls) -> list[str]:
        """Return all roles that have a prompt file in skills/roles/."""
        return sorted(
            p.stem for p in _ROLES_DIR.glob("*.md")
            if not p.stem.startswith("_")
        )


# ── CLI test ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    print("Available roles:", PromptBuilder.available_roles())
    print()

    role = sys.argv[1] if len(sys.argv) > 1 else "credit_analyst"
    builder = PromptBuilder(role)

    sample_data = {
        "name":         "Marcus Johnson",
        "plan":         "pro",
        "stage":        "Fundable",
        "credit_score": "648 personal / no business credit established",
        "goal":         "Access $50K in 0% business credit cards",
        "known_issues": "Two medical collections, one late payment (18 months ago)",
    }

    prompt = builder.build(
        task="Analyze this user's credit profile and identify the top blockers to Tier 1 business credit.",
        user_data=sample_data,
    )

    tokens = builder.estimate_tokens(
        "Analyze this user's credit profile.",
        user_data=sample_data,
    )

    print(f"Role: {role}")
    print(f"Estimated tokens: ~{tokens}")
    print("─" * 60)
    print(prompt)
