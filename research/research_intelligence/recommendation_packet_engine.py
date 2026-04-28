"""
recommendation_packet_engine.py
Reads research artifacts from Supabase, groups them by domain, and writes
compact recommendation packets that Hermes can read and act on.

Packets are written to:
  - Supabase `recommendation_packets` table (upserted by domain)
  - Local JSON file at research/recommendation_packets.json (for fast offline reads)
"""
import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env")
except ImportError:
    pass

logger = logging.getLogger(__name__)

PACKETS_FILE = Path(__file__).parent.parent / "recommendation_packets.json"

DOMAIN_PROMPTS = {
    "trading": (
        "You are a trading strategy analyst. Summarize the key actionable insights, "
        "setups, and risk rules from these research artifacts for a trader to act on today."
    ),
    "credit": (
        "You are a credit and funding advisor. Summarize the key strategies, "
        "tools, and opportunities from these research artifacts for a business owner."
    ),
    "business": (
        "You are a business growth advisor. Summarize the key automation, "
        "income, and scaling strategies from these research artifacts."
    ),
    "tech": (
        "You are a technology analyst. Summarize the key tools, workflows, "
        "and opportunities from these research artifacts."
    ),
    "general": (
        "Summarize the key insights and actionable recommendations from these research artifacts."
    ),
}


def _ensure_table(sb) -> bool:
    """Try to confirm the recommendation_packets table exists via a query."""
    try:
        sb.table("recommendation_packets").select("id").limit(1).execute()
        return True
    except Exception:
        return False


def _build_packet(domain: str, artifacts: List[Dict]) -> str:
    """Build a compact text packet from a list of artifacts."""
    lines = [f"# {domain.upper()} Recommendation Packet", f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ""]
    for a in artifacts[:15]:  # cap at 15 artifacts per domain
        title = a.get("title", "")
        content = a.get("content", "")
        # Extract just the body (skip the Topic/Section/Video header lines)
        body_lines = [l for l in content.split("\n") if not l.startswith(("Topic:", "Section:", "Video:"))]
        body = "\n".join(body_lines).strip()[:600]
        lines.append(f"### {title}")
        lines.append(body)
        lines.append("")
    return "\n".join(lines)


def run(limit: int = 10) -> Dict[str, Any]:
    """
    Build recommendation packets from the research table grouped by domain.
    Returns {"inserted": N, "domains": [list of domains processed]}.
    """
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_KEY not set")

    from supabase import create_client
    sb = create_client(supabase_url, supabase_key)

    # Pull recent artifacts from research table
    try:
        result = sb.table("research").select("source,title,content").limit(limit * 20).execute()
        artifacts = result.data or []
    except Exception as e:
        raise RuntimeError(f"Failed to read research table: {e}")

    if not artifacts:
        return {"inserted": 0, "domains": []}

    # Group by domain
    domain_groups: Dict[str, List[Dict]] = {}
    for a in artifacts:
        source = a.get("source", "")
        # Derive domain from source name using same TOPIC_MAP logic
        domain = _classify_domain(source)
        domain_groups.setdefault(domain, []).append(a)

    has_table = _ensure_table(sb)
    inserted = 0
    domains_processed = []
    all_packets: Dict[str, Any] = {}

    for domain, domain_artifacts in domain_groups.items():
        packet_text = _build_packet(domain, domain_artifacts)
        packet = {
            "domain": domain,
            "artifact_count": len(domain_artifacts),
            "packet": packet_text,
            "generated_at": datetime.now().isoformat(),
        }
        all_packets[domain] = packet
        domains_processed.append(domain)

        if has_table:
            try:
                sb.table("recommendation_packets").upsert(
                    {"domain": domain, "artifact_count": len(domain_artifacts),
                     "packet": packet_text, "generated_at": datetime.now().isoformat()},
                    on_conflict="domain",
                ).execute()
                inserted += 1
            except Exception as e:
                logger.warning("Failed to upsert packet for domain %s: %s", domain, e)

    # Always write local JSON for offline/Hermes access
    PACKETS_FILE.write_text(json.dumps(all_packets, indent=2, default=str), encoding="utf-8")
    logger.info("Recommendation packets: inserted=%d domains=%s", inserted, domains_processed)

    return {"inserted": inserted, "domains": domains_processed}


def _classify_domain(source: str) -> str:
    trading = {"smb capital", "scarface trades", "tradernick", "no nonsense forex"}
    credit  = {"credit plug", "alec delpuech", "stedman waiters"}
    tech    = {"techconversations", "robert's tech toolbox"}
    business = {"jt automations", "monica main"}
    s = source.lower()
    if any(t in s for t in trading):  return "trading"
    if any(t in s for t in credit):   return "credit"
    if any(t in s for t in tech):     return "tech"
    if any(t in s for t in business): return "business"
    return "general"


def get_packet(domain: str) -> Dict[str, Any]:
    """Read a recommendation packet from local cache (fast, no Supabase call)."""
    if PACKETS_FILE.exists():
        try:
            all_packets = json.loads(PACKETS_FILE.read_text(encoding="utf-8"))
            return all_packets.get(domain, {})
        except Exception:
            pass
    return {}


def get_all_packets() -> Dict[str, Any]:
    """Read all recommendation packets from local cache."""
    if PACKETS_FILE.exists():
        try:
            return json.loads(PACKETS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}
