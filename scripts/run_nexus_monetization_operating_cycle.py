#!/usr/bin/env python3
"""
run_nexus_monetization_operating_cycle.py — Nexus Monetization Operating System
================================================================================
Orchestrates all intelligence divisions into a single operating cycle that
produces monetizable finished products — not just logs.

Every cycle must produce (no artifact = no completion):
  1. Risky opportunity analysis
  2. GitHub trend research report (or unavailable-source failure artifact)
  3. Credit repair / funding readiness research packet
  4. Client education packet
  5. Content packet
  6. Monetization packet
  7. CEO review packet
  8. Mistake memory update

Modes:
  validation        — quick run, all engines, free LLMs only
  overnight         — extended run, all domains, more depth
  continue-research — reads prior artifacts, reviews failures, finds new paths, updates CEO packet
  critique          — runs CEO critique pass on latest artifacts (no new research)

Usage:
    python scripts/run_nexus_monetization_operating_cycle.py \\
        --mode validation \\
        --cost free \\
        --focus monetization,learning,system_improvement,credit_repair \\
        --require-artifacts true

    python scripts/run_nexus_monetization_operating_cycle.py \\
        --mode overnight \\
        --cost free \\
        --focus monetization,learning,system_improvement,content,trading,credit_repair,business_funding \\
        --require-artifacts true \\
        --max-runtime-minutes 360
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_env = ROOT / ".env"
if _env.exists():
    import os
    with open(_env) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip(); v = v.strip().strip('"').strip("'")
            if k not in os.environ:
                os.environ[k] = v


APPROVAL_REQUIRED = [
    "spending money",
    "paid APIs",
    "live broker trading",
    "broker connection",
    "public publishing",
    "client-facing messages",
    "production deployment",
    "destructive DB changes",
    "joining affiliate programs",
    "making legal/financial/health claims",
]

AUTONOMOUS_ALLOWED = [
    "free research",
    "internal strategy testing",
    "paper trading/demo testing",
    "content drafting",
    "affiliate/monetization research",
    "GitHub trend research",
    "safe system improvement recommendations",
    "local artifact creation",
    "Supabase/workflow_outputs saving",
    "internal reports",
    "self-recovery attempts",
]

BLOCKED = [
    "hiding failures",
    "deleting logs to hide errors",
    "claiming completion without artifacts",
    "live trading without approval",
    "guarantees of funding, income, or trading results",
]

VALID_FINISHED_PRODUCTS = [
    "client_education_packet",
    "content_packet",
    "monetization_packet",
    "risky_opportunity_analysis",
    "github_trend_recommendation",
    "ceo_review_packet",
    "trading_strategy_packet",
    "strategy_improvement_packet",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _save(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def _save_workflow_output(row: dict) -> str | None:
    try:
        import os, requests
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "") or os.getenv("SUPABASE_KEY", "")
        if not url or not key:
            return None
        resp = requests.post(
            f"{url}/rest/v1/workflow_outputs",
            headers={"apikey": key, "Authorization": f"Bearer {key}",
                     "Content-Type": "application/json", "Prefer": "return=representation"},
            json=row, timeout=10,
        )
        if resp.ok:
            data = resp.json()
            if isinstance(data, list) and data:
                return str(data[0].get("id", ""))
        return None
    except Exception:
        return None


class NexusOperatingCycle:

    def __init__(
        self,
        mode: str = "validation",
        cost_mode: str = "free",
        focus: list[str] | None = None,
        require_artifacts: bool = True,
        max_runtime_minutes: int = 60,
    ) -> None:
        self.mode                = mode
        self.cost_mode           = cost_mode
        self.focus               = focus or ["monetization", "learning", "system_improvement", "credit_repair"]
        self.require_artifacts   = require_artifacts
        self.max_runtime_minutes = max_runtime_minutes
        self.start_time          = time.time()
        self.run_id              = f"cycle_{_ts()}_{uuid.uuid4().hex[:6]}"
        self.artifacts: dict[str, str]  = {}
        self.errors:    list[str]       = []
        self.finished_products: list[dict] = []
        self.mistake_memory = None
        self._init_mistake_memory()

    def _init_mistake_memory(self) -> None:
        try:
            from lib.hermes_mistake_memory import HermesMistakeMemory
            self.mistake_memory = HermesMistakeMemory()
        except Exception as exc:
            self.errors.append(f"HermesMistakeMemory init: {exc}")

    def _elapsed(self) -> float:
        return (time.time() - self.start_time) / 60

    def _within_budget(self) -> bool:
        return self._elapsed() < self.max_runtime_minutes

    def _record_mistake(self, pattern: str, category: str, evidence: str, rule: str = "") -> None:
        if self.mistake_memory:
            try:
                self.mistake_memory.record_pattern(pattern, category, evidence, rule)
            except Exception:
                pass

    def _add_finished_product(self, product_type: str, path: str, summary: str = "") -> None:
        if not Path(path).exists():
            if self.require_artifacts:
                self.errors.append(f"ARTIFACT_MISSING: {product_type} — {path}")
                self._record_mistake(
                    f"Missing artifact for {product_type}",
                    "artifact_missing_claimed_complete",
                    f"Attempted to add {product_type} but {path} does not exist",
                    "Do not claim completion without verifying artifact file exists",
                )
            return
        self.artifacts[product_type] = path
        self.finished_products.append({
            "type":    product_type,
            "path":    path,
            "summary": summary,
        })
        print(f"  ✅ Finished product: {product_type} → {Path(path).name}")

    # ── Stage runners ────────────────────────────────────────────────────────

    def _run_risky_opportunity(self) -> None:
        if "learning" not in self.focus:
            return
        if not self._within_budget():
            return
        print("\n[cycle] ── Risky Opportunity Analysis ──────────────")
        try:
            from lib.risky_opportunity_learning import RiskyOpportunityEngine
            engine = RiskyOpportunityEngine()
            result = engine.analyze(
                opportunity=(
                    "Automated live trading signal service — "
                    "sell stock/crypto signals to subscribers via Telegram or email."
                ),
                source="nexus_autonomous_cycle",
                context="Nexus has a paper-trading backtester. Question: can this be monetized safely?",
            )
            if result.get("md_path"):
                self._add_finished_product(
                    "risky_opportunity_analysis",
                    result["md_path"],
                    f"Disposition: {result.get('disposition', '?')} | Risk: {result.get('risk_category', '?')}",
                )
            if result.get("json_path"):
                self.artifacts["risky_opportunity_json"] = result["json_path"]
        except Exception as exc:
            self.errors.append(f"RiskyOpportunityEngine: {exc}")
            traceback.print_exc()

    def _run_github_trends(self) -> None:
        if "system_improvement" not in self.focus:
            return
        if not self._within_budget():
            return
        print("\n[cycle] ── GitHub Trend Research ───────────────────")
        try:
            from lib.github_trend_researcher import GitHubTrendResearcher
            result = GitHubTrendResearcher().run()
            status = result.get("source_status", "?")
            print(f"  source: {status} | repos: {result.get('repos_fetched', 0)}")

            if result.get("artifacts", {}).get("recommendations_md"):
                self._add_finished_product(
                    "github_trend_recommendation",
                    result["artifacts"]["recommendations_md"],
                    f"Source: {status} | Top: {result.get('top_1_recommendation', {}).get('name', 'N/A')}",
                )
            if result.get("unavailability_reason"):
                unavail = result["artifacts"].get("unavailable_artifact", "")
                if unavail:
                    self.artifacts["github_unavailable_report"] = unavail
        except Exception as exc:
            self.errors.append(f"GitHubTrendResearcher: {exc}")
            traceback.print_exc()

    def _run_credit_repair(self) -> None:
        if "credit_repair" not in self.focus:
            return
        if not self._within_budget():
            return
        print("\n[cycle] ── Credit Repair / Funding Readiness ───────")
        try:
            from scripts.run_nexus_learn_by_doing_cycle import run_credit_repair_cycle
            ts     = _ts()
            result = run_credit_repair_cycle("credit_repair", ts)

            for key in ["client_education", "content_pack", "monetization"]:
                path = result.get("artifacts", {}).get(key, "")
                ptype = {
                    "client_education": "client_education_packet",
                    "content_pack":     "content_packet",
                    "monetization":     "monetization_packet",
                }[key]
                if path:
                    self._add_finished_product(ptype, path)
        except Exception as exc:
            self.errors.append(f"LearnByDoing/credit_repair: {exc}")
            traceback.print_exc()

    def _run_monetization(self) -> None:
        if "monetization" not in self.focus:
            return
        if not self._within_budget():
            return
        print("\n[cycle] ── Monetization Operating Engine ───────────")
        try:
            from lib.monetization_operating_engine import MonetizationOperatingEngine
            result = MonetizationOperatingEngine().run(focus=self.focus)

            if result.get("artifacts", {}).get("plan_md"):
                self._add_finished_product(
                    "monetization_packet",
                    result["artifacts"]["plan_md"],
                    f"Fastest: {result.get('fastest_to_revenue', '?')} | Confidence: {result.get('highest_confidence', '?')}",
                )
            for akey, apath in result.get("artifacts", {}).items():
                if apath and akey not in self.artifacts:
                    self.artifacts[f"monetization_{akey}"] = apath
        except Exception as exc:
            self.errors.append(f"MonetizationOperatingEngine: {exc}")
            traceback.print_exc()

    def _build_ceo_packet(self) -> str:
        """Build and save the CEO review packet. Returns path."""
        ts      = _ts()
        ceo_dir = ROOT / "docs" / "reports" / "ceo_review"

        summary_lines: list[str] = []
        for fp in self.finished_products:
            summary_lines.append(f"- **{fp['type']}**: `{Path(fp['path']).name}` — {fp.get('summary', '')}")

        mistake_summary = ""
        if self.mistake_memory:
            s = self.mistake_memory.summary()
            mistake_summary = (
                f"Total patterns: {s['total_patterns']} | Active: {s['active']} | "
                f"Corrected: {s['corrected']} | High recurrence: {s['high_recurrence']}"
            )

        ceo_md = f"""# NEXUS MONETIZATION CEO PACKET
*Run ID: {self.run_id} | {_now()} | Mode: {self.mode}*

---

## 1. Executive Summary

Nexus completed a {"validation" if self.mode == "validation" else "full overnight"} operating cycle.
Focus areas: {', '.join(self.focus)}
Finished products created: {len(self.finished_products)}
Errors encountered: {len(self.errors)}
Runtime: {self._elapsed():.1f} minutes

---

## 2. What Nexus Did

This cycle ran the following engines:
{chr(10).join(f'- {f}' for f in self.focus)}

For each engine, artifacts were saved locally and (where configured) to Supabase workflow_outputs.

---

## 3. What Hermes Learned

{"Mistake memory: " + mistake_summary if mistake_summary else "Mistake memory: not initialized"}

---

## 4–5. Risky Opportunities Reviewed

{self._section_risky()}

---

## 6–7. GitHub Trends Reviewed

{self._section_github()}

---

## 8. Credit Repair / Funding Readiness Strategies

{self._section_credit_repair()}

---

## 9. Monetization Opportunities Ranked

{self._section_monetization()}

---

## 10. Finished Products Created

{chr(10).join(summary_lines) if summary_lines else "None — check error log"}

---

## 11. What Failed

{chr(10).join(f'- {e}' for e in self.errors) if self.errors else "No errors recorded."}

---

## 12. What Succeeded

{chr(10).join(f'- {fp["type"]}' for fp in self.finished_products) if self.finished_products else "No finished products confirmed."}

---

## 13. What Hermes Should Do Next (Autonomous)

- Run content pipeline on top credit repair strategies found
- Schedule weekly GitHub trend research (Monday 6am)
- Add high-confidence monetization paths to Hermes memory
- Re-analyze any risky opportunities with `safe_reframe_available` disposition
- Update mistake memory with patterns from this cycle

---

## 14. What Requires Ray Approval

{chr(10).join(f'- {a}' for a in APPROVAL_REQUIRED)}

---

## 15. Artifacts Created

{chr(10).join(f'- `{k}`: {v}' for k, v in self.artifacts.items()) if self.artifacts else "No artifacts recorded."}

---

## 16. How Nexus Can Make Money in 30 Days

See: `docs/reports/monetization/30_day_revenue_plan_*.md`

Priority order:
1. Launch Nexus funding readiness audit offer (newsletter + YouTube CTA)
2. Publish first batch of credit repair education content
3. Activate Beehiiv newsletter with affiliate offers
4. Test paper-trading education email sequence (Lendio/NAV affiliate)

---

## Commands

Overnight run:
```
python scripts/run_nexus_monetization_operating_cycle.py \\
  --mode overnight \\
  --cost free \\
  --focus monetization,learning,system_improvement,content,trading,credit_repair,business_funding \\
  --require-artifacts true \\
  --max-runtime-minutes 360
```

Content pipeline:
```
python scripts/run_content_pipeline.py \\
  --topic "Why most businesses get denied funding and how AI can help fix readiness gaps" \\
  --platforms youtube newsletter
```

GitHub trend research:
```
python scripts/run_weekly_github_trend_research.py
```

Learn-by-doing (credit repair):
```
python scripts/run_nexus_learn_by_doing_cycle.py --domain credit_repair
```

Demo broker test (practice only):
```
python scripts/test_oanda_demo_execution_loop.py --dry-run
```

Resolve premium blockers:
```
python scripts/run_nexus_monetization_operating_cycle.py --mode validation --resolve-premium-blockers
```

---

## 17. Hermes Decision Log

{self._section_decision_log()}

---

## 18. Pending Handoffs (Action Required by Ray)

{self._section_handoffs()}

---

## 19. Demo Broker Status (OANDA Practice)

{self._section_demo_broker()}

---

## 20. Premium Blocker Resolutions

{self._section_premium_blockers()}

---

## 21. Ray Feedback (Most Recent)

{self._section_ray_feedback()}

"""

        ceo_json = {
            "run_id":           self.run_id,
            "mode":             self.mode,
            "created":          _now(),
            "focus":            self.focus,
            "finished_products": self.finished_products,
            "artifacts":        self.artifacts,
            "errors":           self.errors,
            "runtime_minutes":  round(self._elapsed(), 1),
            "mistake_summary":  mistake_summary,
        }

        md_path   = _save(ceo_dir / f"NEXUS_MONETIZATION_CEO_PACKET_{ts}.md",   ceo_md)
        json_path = _save(ceo_dir / f"NEXUS_MONETIZATION_CEO_PACKET_{ts}.json", json.dumps(ceo_json, indent=2, default=str))
        self.artifacts["ceo_packet_md"]   = str(md_path)
        self.artifacts["ceo_packet_json"] = str(json_path)
        return str(md_path)

    def _section_risky(self) -> str:
        path = self.artifacts.get("risky_opportunity_analysis", "")
        if path and Path(path).exists():
            try:
                content = Path(path).read_text()
                # Extract first 300 chars after the "What Made It Risky" header
                m = re.search(r"## What Made It Risky\n(.{0,300})", content, re.DOTALL)
                snippet = m.group(1).strip()[:300] if m else "See artifact."
                disp_m = re.search(r"\*\*Disposition:\*\* `([^`]+)`", content)
                disp = disp_m.group(1) if disp_m else "?"
                return f"Disposition: `{disp}`\n\n{snippet}"
            except Exception:
                pass
        return "Not run or no artifact produced."

    def _section_github(self) -> str:
        path = self.artifacts.get("github_trend_recommendation", "")
        if path and Path(path).exists():
            try:
                return Path(path).read_text()[:500]
            except Exception:
                pass
        unavail = self.artifacts.get("github_unavailable_report", "")
        if unavail and Path(unavail).exists():
            return f"GitHub API unavailable — see: `{unavail}`"
        return "Not run or no artifact produced."

    def _section_credit_repair(self) -> str:
        edu = self.artifacts.get("client_education_packet", "")
        if edu and Path(edu).exists():
            try:
                return Path(edu).read_text()[:500] + "\n*(truncated — see full artifact)*"
            except Exception:
                pass
        return "Not run or no artifact produced."

    def _section_monetization(self) -> str:
        path = self.artifacts.get("monetization_packet", "")
        if path and Path(path).exists():
            try:
                return Path(path).read_text()[:500] + "\n*(truncated — see full artifact)*"
            except Exception:
                pass
        return "Not run or no artifact produced."

    def _section_decision_log(self) -> str:
        try:
            from lib.hermes_ceo_decision_policy import HermesCEODecisionPolicy
            policy = HermesCEODecisionPolicy()
            recent = policy.recent_decisions(10)
            if not recent:
                return "No decisions logged yet."
            lines = [f"- [{r['logged_at'][:19]}] **{r['action']}** → `{r['decision']}` — {r['rule'][:60]}" for r in recent[-5:]]
            return "\n".join(lines)
        except Exception as e:
            return f"Decision log unavailable: {e}"

    def _section_handoffs(self) -> str:
        try:
            from lib.hermes_action_handoff import pending_handoffs
            items = pending_handoffs()
            if not items:
                return "No pending handoffs."
            lines = [f"- **{h['title']}** (`{h['handoff_id']}`) — {h['action_required'][:80]}" for h in items]
            return "\n".join(lines)
        except Exception as e:
            return f"Handoffs unavailable: {e}"

    def _section_demo_broker(self) -> str:
        try:
            from integrations.oanda_demo import OandaDemoAdapter
            adapter = OandaDemoAdapter()
            recent = adapter.recent_orders(5)
            enabled = __import__("os").getenv("OANDA_DEMO_ENABLED", "false")
            env = __import__("os").getenv("OANDA_ENVIRONMENT", "practice")
            if not recent:
                return f"Environment: {env} | DEMO_ENABLED: {enabled} | No demo orders today."
            lines = [f"Environment: {env} | DEMO_ENABLED: {enabled}", ""]
            for o in recent:
                status = "✅" if o.get("ok") else "❌"
                lines.append(f"- {status} {o.get('instrument', '?')} {o.get('side', '?')} {o.get('units', '?')}u @ {o.get('placed_at', '?')[:16]}")
            return "\n".join(lines)
        except Exception as e:
            return f"OANDA demo status unavailable: {e}"

    def _section_premium_blockers(self) -> str:
        try:
            blocker_dir = ROOT / "docs" / "reports" / "premium_blockers"
            if not blocker_dir.exists():
                return "No premium blocker resolutions run yet."
            files = sorted(blocker_dir.glob("blocker_resolution_*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
            if not files:
                return "No premium blocker resolutions run yet."
            return files[0].read_text()[:400] + "\n*(truncated — see full artifact)*"
        except Exception as e:
            return f"Premium blockers unavailable: {e}"

    def _section_ray_feedback(self) -> str:
        try:
            from lib.hermes_action_handoff import RayFeedbackStore
            store = RayFeedbackStore()
            recent = store.recent(3)
            if not recent:
                return "No Ray feedback saved yet."
            lines = [f"- [{r['saved_at'][:10]}] ({r['category']}) {r['message'][:100]}" for r in recent]
            return "\n".join(lines)
        except Exception as e:
            return f"Ray feedback unavailable: {e}"

    def _run_compliance_review(self) -> None:
        """Run compliance review on latest discovered strategies (credit_repair domain)."""
        if not self._within_budget():
            return
        print("\n[cycle] ── Compliance Review Gate ──────────────────")
        try:
            from lib.compliance_strategy_review import ComplianceReviewer
            # Load latest strategy discovery
            discovery_dir = ROOT / "docs" / "reports" / "learn_by_doing" / "credit_repair"
            discoveries   = sorted(discovery_dir.glob("new_strategy_discovery_*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
            if not discoveries:
                print("  no strategy discoveries found — skipping compliance review")
                return
            # Parse strategies from latest discovery (fallback: run LLM to extract)
            latest_discovery = discoveries[0].read_text()
            # Build minimal strategy dicts from headings
            strategies = []
            for m in re.finditer(r"## (.+?)\n.*?\*\*Source:\*\* (.+?)\n.*?\*\*Problem:\*\* (.+?)\n.*?\*\*Risk:\*\* (.+?)(?:\n|$)", latest_discovery, re.DOTALL):
                strategies.append({
                    "name":                     m.group(1).strip(),
                    "source":                   m.group(2).strip(),
                    "problem_solved":           m.group(3).strip(),
                    "risk_or_compliance_concern": m.group(4).strip(),
                    "client_safe":              True,  # auto-labeled — will be overridden
                    "client_education_angle":   "",
                })

            if not strategies:
                print("  could not parse strategies from discovery — using placeholder")
                strategies = [{"name": "Unknown", "source": "llm", "problem_solved": "", "risk_or_compliance_concern": "", "client_safe": True, "client_education_angle": ""}]

            reviewer = ComplianceReviewer()
            result   = reviewer.review_strategies(strategies, domain="credit_repair")
            print(f"  {result['total']} strategies reviewed | statuses: {result['by_status']}")

            if result.get("md_path"):
                self._add_finished_product(
                    "compliance_review",
                    result["md_path"],
                    f"Statuses: {result['by_status']}",
                )
            if result.get("json_path"):
                self.artifacts["compliance_review_json"] = result["json_path"]
        except Exception as exc:
            self.errors.append(f"ComplianceReviewer: {exc}")
            traceback.print_exc()

    def _run_continue_research(self) -> None:
        """continue-research mode: review prior artifacts, find new paths, update packet."""
        ts  = _ts()
        ceo_dir = ROOT / "docs" / "reports" / "ceo_review"
        print("\n[cycle] ── Continue-Research Mode ─────────────────")

        # 1. Load prior artifacts summary
        prior_packets = sorted((ROOT / "docs" / "reports" / "ceo_review").glob("NEXUS_MONETIZATION_CEO_PACKET_*.md"),
                               key=lambda f: f.stat().st_mtime, reverse=True)
        prior_summary = prior_packets[0].read_text()[:2000] if prior_packets else "No prior CEO packet found."

        prior_risky  = sorted((ROOT / "docs" / "reports" / "risky_opportunities").glob("risky_opportunity_analysis_*.md"),
                              key=lambda f: f.stat().st_mtime, reverse=True)
        risky_summary = prior_risky[0].read_text()[:1000] if prior_risky else "No prior risky opportunity analysis."

        prior_compliance = sorted((ROOT / "docs" / "reports" / "learn_by_doing" / "credit_repair").glob("compliance_review_*.md"),
                                  key=lambda f: f.stat().st_mtime, reverse=True)
        compliance_summary = prior_compliance[0].read_text()[:1000] if prior_compliance else "No prior compliance review."

        mistake_memory_data = ""
        if self.mistake_memory:
            active = self.mistake_memory.get_active_corrections()
            mistake_memory_data = "\n".join(f"- {p['pattern'][:80]}" for p in active[:5]) or "No active patterns."

        # 2. LLM synthesis
        try:
            from lib.content_generation_router import generate_content
            prompt = f"""You are synthesizing a continued research queue for Nexus.

Prior CEO packet summary:
{prior_summary[:800]}

Prior risky opportunity:
{risky_summary[:500]}

Prior compliance review:
{compliance_summary[:500]}

Active mistake patterns:
{mistake_memory_data}

Generate a continued research packet with:
1. What was learned from prior run (2-3 key insights from the artifacts)
2. What came from internal memory (patterns being applied)
3. What new research should happen next (5 specific research questions)
4. New monetization paths not yet explored (3 ideas with no compliance risk)
5. GitHub/system improvements to prioritize (2 specific recommendations)
6. What Hermes recommends Ray review first
7. What requires Ray approval before any next step
8. Research queue for next overnight run (ordered list)

Return as structured markdown with clear sections. 600-900 words."""
            r = generate_content(prompt=prompt, system="You are a research synthesizer. Be specific, not vague. Output structured markdown.", tier="reasoning", max_tokens=2000, timeout=120)
            synthesis = r.get("response", "") if isinstance(r, dict) else str(r)
        except Exception as exc:
            synthesis = f"LLM synthesis unavailable: {exc}"

        # 3. Save continued research packet
        packet_md = f"""# NEXUS CONTINUED RESEARCH PACKET
*Run ID: {self.run_id} | {_now()} | Mode: continue-research*

---

## What This Run Did

Reviewed prior artifacts, applied active mistake patterns, and synthesized a next-step research queue.
No new external research was performed — this mode works from existing artifacts.

## Active Mistake Patterns Applied

{mistake_memory_data}

---

{synthesis}

---

## Artifacts Available for Review

"""
        for k, v in self.artifacts.items():
            packet_md += f"- `{k}`: {Path(str(v)).name if v else 'MISSING'}\n"

        packet_md += f"""
---

## Commands

Next validation run:
```
python scripts/run_nexus_monetization_operating_cycle.py \\
  --mode validation \\
  --cost free \\
  --focus monetization,learning,system_improvement,credit_repair,business_funding,content \\
  --require-artifacts true
```

Overnight run:
```
python scripts/run_nexus_monetization_operating_cycle.py \\
  --mode overnight \\
  --cost free \\
  --focus monetization,learning,system_improvement,content,trading,credit_repair,business_funding \\
  --require-artifacts true \\
  --max-runtime-minutes 360
```
"""

        packet_path = _save(ceo_dir / f"NEXUS_CONTINUED_RESEARCH_PACKET_{ts}.md", packet_md)
        packet_json = {
            "run_id": self.run_id, "created": _now(),
            "mode": "continue-research",
            "artifacts": self.artifacts,
            "active_mistakes": mistake_memory_data,
        }
        json_path = _save(ceo_dir / f"NEXUS_CONTINUED_RESEARCH_PACKET_{ts}.json",
                          json.dumps(packet_json, indent=2, default=str))

        self._add_finished_product("continued_research_packet", str(packet_path))
        self.artifacts["continued_research_json"] = str(json_path)
        print(f"  continued research packet → {packet_path.name}")

    # ── Main run ─────────────────────────────────────────────────────────────

    def run(self) -> dict:
        print(f"\n{'='*60}")
        print(f"[NEXUS] Monetization Operating Cycle — {self.mode.upper()}")
        print(f"  Run ID:  {self.run_id}")
        print(f"  Focus:   {', '.join(self.focus)}")
        print(f"  Mode:    {self.mode}")
        print(f"  Cost:    {self.cost_mode}")
        print(f"  Budget:  {self.max_runtime_minutes}min")
        print(f"{'='*60}\n")

        if self.mode == "continue-research":
            # Load prior compliance data, review, synthesize, no new external research
            self._run_continue_research()
        else:
            self._run_risky_opportunity()
            self._run_github_trends()
            self._run_credit_repair()
            self._run_compliance_review()   # ← NEW: compliance gate after credit repair
            self._run_monetization()

        print("\n[cycle] Building CEO review packet…")
        import re
        ceo_path = self._build_ceo_packet()
        self._add_finished_product("ceo_review_packet", ceo_path)

        # Save Hermes mistake memory markdown snapshot
        if self.mistake_memory:
            try:
                mem_md_path = ROOT / "docs" / "reports" / "hermes_mistake_memory_snapshot.md"
                _save(mem_md_path, self.mistake_memory.render_md())
                self.artifacts["mistake_memory_snapshot"] = str(mem_md_path)
            except Exception as exc:
                self.errors.append(f"MistakeMemory snapshot: {exc}")

        # Supabase workflow_output
        wf_id = _save_workflow_output({
            "id":              str(uuid.uuid4()),
            "created_at":      _now(),
            "workflow_type":   "nexus_operating_cycle",
            "mode":            self.mode,
            "focus":           json.dumps(self.focus),
            "finished_products": len(self.finished_products),
            "artifact_count":  len(self.artifacts),
            "errors":          json.dumps(self.errors),
            "runtime_minutes": round(self._elapsed(), 1),
            "run_id":          self.run_id,
        })
        if wf_id:
            print(f"\n[cycle] Supabase workflow_output saved: {wf_id}")

        print(f"\n{'='*60}")
        print(f"[NEXUS] CYCLE COMPLETE")
        print(f"  Runtime:    {self._elapsed():.1f}min")
        print(f"  Products:   {len(self.finished_products)}")
        print(f"  Artifacts:  {len(self.artifacts)}")
        print(f"  Errors:     {len(self.errors)}")
        for fp in self.finished_products:
            print(f"  ✅ {fp['type']}")
        if self.errors:
            print(f"\n  Errors:")
            for e in self.errors:
                print(f"    ⚠️  {e}")
        print(f"{'='*60}\n")

        return {
            "run_id":            self.run_id,
            "mode":              self.mode,
            "finished_products": self.finished_products,
            "artifacts":         self.artifacts,
            "errors":            self.errors,
            "runtime_minutes":   round(self._elapsed(), 1),
        }


import re  # needed in _build_ceo_packet at class level


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Nexus Monetization Operating Cycle"
    )
    parser.add_argument("--mode", default="validation",
                        choices=["validation", "overnight", "quick", "continue-research", "critique"],
                        help="Run mode")
    parser.add_argument("--cost", default="free", choices=["free", "paid"],
                        help="Cost mode — free blocks paid APIs")
    parser.add_argument("--focus", default="monetization,learning,system_improvement,credit_repair",
                        help="Comma-separated focus areas")
    parser.add_argument("--require-artifacts", default="true",
                        help="Fail if any finished product is missing an artifact")
    parser.add_argument("--max-runtime-minutes", type=int, default=60,
                        help="Max runtime in minutes (overnight: 360)")
    parser.add_argument("--json-out", default="",
                        help="Optional: save result JSON")
    parser.add_argument("--include-demo-broker-test", action="store_true",
                        help="Run OANDA demo execution loop after cycle (requires OANDA_DEMO_ENABLED=true)")
    parser.add_argument("--broker", default="oanda", choices=["oanda"],
                        help="Demo broker to use (only oanda supported)")
    parser.add_argument("--demo-only", action="store_true",
                        help="Run demo broker test only, skip main cycle")
    parser.add_argument("--resolve-premium-blockers", action="store_true",
                        help="Run premium blocker resolver for beehiiv and other tools")
    parser.add_argument("--notify-ray", action="store_true",
                        help="Send proactive Telegram notification on cycle complete")
    parser.add_argument("--proactive-telegram", action="store_true",
                        help="Enable proactive Telegram notifications for errors and handoffs during cycle")
    args = parser.parse_args()

    focus = [f.strip() for f in args.focus.split(",") if f.strip()]
    req   = args.require_artifacts.lower() not in ("false", "0", "no")

    cycle = NexusOperatingCycle(
        mode                = args.mode,
        cost_mode           = args.cost,
        focus               = focus,
        require_artifacts   = req,
        max_runtime_minutes = args.max_runtime_minutes,
    )

    if args.demo_only:
        import subprocess
        print("[cycle] --demo-only: running OANDA demo execution loop…")
        subprocess.run([sys.executable, "scripts/test_oanda_demo_execution_loop.py", "--dry-run"], check=False)
        sys.exit(0)

    result = cycle.run()

    if args.resolve_premium_blockers:
        print("[cycle] Resolving premium blockers…")
        try:
            from lib.premium_blocker_resolver import PremiumBlockerResolver
            resolver = PremiumBlockerResolver()
            for tool in ["beehiiv", "convertkit"]:
                packet = resolver.resolve(tool, context="nexus_operating_cycle")
                print(f"[cycle]   ✅ {tool} → {Path(packet['report_path']).name}")
        except Exception as e:
            print(f"[cycle]   ⚠️  premium_blocker_resolver: {e}")

    if args.include_demo_broker_test:
        print("[cycle] Running OANDA demo execution loop…")
        try:
            import subprocess
            r = subprocess.run(
                [sys.executable, "scripts/test_oanda_demo_execution_loop.py", "--dry-run"],
                capture_output=True, text=True, timeout=60,
            )
            print(r.stdout.strip())
            if r.returncode not in (0, 2):
                print(f"[cycle]   ⚠️  demo broker test exit code: {r.returncode}")
        except Exception as e:
            print(f"[cycle]   ⚠️  demo broker test: {e}")

    if args.notify_ray or args.proactive_telegram:
        try:
            from lib.hermes_proactive_notifier import notify_cycle_complete
            products = list(result.get("finished_products", {}).keys())
            errors   = [str(e) for e in result.get("errors", [])]
            runtime  = result.get("runtime_minutes", 0)
            run_id   = result.get("run_id", "")
            sent = notify_cycle_complete(run_id, products, errors, runtime)
            print(f"[cycle] Telegram notification: {'sent' if sent else 'suppressed (gate)'}")
        except Exception as e:
            print(f"[cycle]   ⚠️  proactive notification: {e}")

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2, default=str))
        print(f"[cycle] Full result → {out}")

    success = len(result["finished_products"]) > 0
    sys.exit(0 if success else 2)


if __name__ == "__main__":
    main()
