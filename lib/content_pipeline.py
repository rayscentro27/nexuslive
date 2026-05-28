"""
content_pipeline.py — Nexus Content Engine Orchestrator
========================================================
Chains all 7 agents into a single run and enforces the anti-demo rule:
  No artifact = no completion.

Every successful run produces:
  - research brief  (docs/content/research_briefs/)
  - hook options    (docs/content/hooks/)
  - hook report     (docs/content/hooks/)
  - platform draft  (docs/content/{platform}_scripts/ or newsletters/)
  - approval packet (docs/content/approval_packets/)
  - Discord delivery (Content Engine channel)
  - workflow_output row in Supabase

Usage:
    from lib.content_pipeline import ContentPipeline
    result = ContentPipeline().run(
        topic="Why most businesses get denied funding...",
        platforms=["youtube", "newsletter"],
    )

CLI:
    python scripts/run_content_pipeline.py \\
        --topic "Why most businesses get denied funding and how AI can help fix readiness gaps" \\
        --platforms youtube newsletter
"""
from __future__ import annotations

import json
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

from lib.content_agents import (
    ResearchAgent,
    HookAgent,
    HookGatekeeper,
    ScriptBuilder,
    LineEditor,
    MonetizationAgent,
    ApprovalAgent,
)


# ── Supabase workflow_output helper ───────────────────────────────────────────

def _save_workflow_output(row: dict) -> str | None:
    """Save a workflow_output row to Supabase. Returns row id or None."""
    try:
        import os, requests
        url  = os.getenv("SUPABASE_URL", "")
        key  = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "") or os.getenv("SUPABASE_KEY", "")
        if not url or not key:
            return None
        resp = requests.post(
            f"{url}/rest/v1/workflow_outputs",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type":  "application/json",
                "Prefer":        "return=representation",
            },
            json=row,
            timeout=10,
        )
        if resp.ok:
            data = resp.json()
            if isinstance(data, list) and data:
                return str(data[0].get("id", ""))
        return None
    except Exception:
        return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Discord delivery helper ───────────────────────────────────────────────────

def _discord_deliver(packet: dict, topic: str, platform: str) -> bool:
    """Send approval packet summary to the Discord Content Engine channel."""
    try:
        from lib.discord_notifier import content as dc

        status      = packet.get("status", "unknown")
        overall     = packet.get("overall_score", 0)
        approval_id = packet.get("approval_id", "")
        hook        = packet.get("hook", "")
        word_count  = packet.get("word_count", 0)
        primary_cta = packet.get("primary_cta", "")
        artifacts   = packet.get("artifacts", {})
        scores      = packet.get("scores", {})

        status_emoji = "✅" if status == "approval_ready" else "⚠️"
        status_label = "APPROVAL READY" if status == "approval_ready" else "NEEDS REVISION"

        # Build body for send_draft
        lines = [
            f"**Hook:** {hook[:200]}",
            f"**Platform:** {platform.upper()}",
            f"**Status:** {status_emoji} {status_label}",
            f"**Overall Score:** {overall:.1f}/100",
            "",
            "**Scores:**",
        ]
        for k, v in scores.items():
            lines.append(f"  • {k.replace('_', ' ').title()}: {v:.1f}")

        if primary_cta:
            lines.append(f"\n**Primary CTA:** {primary_cta[:200]}")

        if artifacts:
            lines.append("\n**Artifacts saved:**")
            # artifacts from ApprovalAgent is a list of paths; from pipeline _run_platform it's a dict
            if isinstance(artifacts, dict):
                for k, v in artifacts.items():
                    if v:
                        lines.append(f"  • {k}: `{Path(str(v)).name}`")
            else:
                for v in artifacts:
                    if v:
                        lines.append(f"  • `{Path(str(v)).name}`")

        if status == "approval_ready":
            lines.append(f"\n**Approve:** `approve content {approval_id}`")
            lines.append(f"**Reject:**  `reject content {approval_id}`")

        body = "\n".join(lines)

        return dc.send_draft(
            content_type="youtube_script" if platform == "youtube" else "newsletter",
            title=f"[{platform.upper()}] {topic[:120]}",
            body=body,
            topic=topic[:200],
            word_count=word_count,
            quality_score=int(overall),
            row_id=approval_id,
        )
    except Exception as exc:
        print(f"[pipeline] Discord delivery error: {exc}")
        return False


# ── Pipeline ──────────────────────────────────────────────────────────────────

class ContentPipeline:
    """
    Orchestrates all 7 content agents end-to-end for one topic + N platforms.
    """

    def __init__(self) -> None:
        self.research   = ResearchAgent()
        self.hooks      = HookAgent()
        self.gatekeeper = HookGatekeeper()
        self.builder    = ScriptBuilder()
        self.editor     = LineEditor()
        self.monetizer  = MonetizationAgent()
        self.approver   = ApprovalAgent()

    # ── internal ──────────────────────────────────────────────────────────────

    def _run_platform(
        self,
        topic: str,
        platform: str,
        brief: dict,
        hook_result: dict,
    ) -> dict:
        """Run draft → edit → monetize → approve for one platform."""
        run_id = str(uuid.uuid4())[:8]
        errors: list[str] = []
        artifacts: dict   = {}
        workflow_id: str | None = None

        # ── Stage 3: Draft ────────────────────────────────────────────────────
        # best_hook may be a string or a dict depending on the gatekeeper version
        _best = hook_result.get("best_hook", "")
        best_hook_text = _best if isinstance(_best, str) else _best.get("hook", str(_best))

        print(f"  [stage 3/{platform}] Building {platform} script…")
        try:
            draft = self.builder.build(
                topic    = topic,
                platform = platform,
                hook     = best_hook_text,
                brief    = brief,
            )
            artifacts["draft"] = draft.get("saved_path", "")
            print(f"    draft: {draft.get('word_count', 0)} words → {artifacts['draft']}")
        except Exception as exc:
            errors.append(f"ScriptBuilder: {exc}")
            traceback.print_exc()
            draft = {"full_text": "", "sections": [], "word_count": 0, "saved_path": ""}

        if not draft.get("full_text"):
            errors.append("ScriptBuilder: empty draft — no artifact produced")

        # ── Stage 4: Line editing ─────────────────────────────────────────────
        print(f"  [stage 4/{platform}] Line editing…")
        try:
            edited = self.editor.score_and_rewrite(draft=draft, brief=brief)
            print(f"    section score: {edited.get('overall_section_score', 0):.2f} | rewrites: {edited.get('rewrites_applied', 0)}")
        except Exception as exc:
            errors.append(f"LineEditor: {exc}")
            traceback.print_exc()
            edited = {
                "improved_text":      draft.get("full_text", ""),
                "scored_sections":    [],
                "overall_section_score": 0.0,
                "rewrites_applied":   0,
            }

        # ── Stage 5: Monetization ─────────────────────────────────────────────
        print(f"  [stage 5/{platform}] Adding CTA…")
        try:
            monetization = self.monetizer.add_cta(
                improved_text = edited.get("improved_text", ""),
                topic         = topic,
                platform      = platform,
                brief         = brief,
            )
            artifacts["monetized"] = monetization.get("saved_path", "")
            print(f"    CTA: {monetization.get('primary_cta', '')[:80]}")
        except Exception as exc:
            errors.append(f"MonetizationAgent: {exc}")
            traceback.print_exc()
            monetization = {
                "primary_cta":       "",
                "full_cta_section":  "",
                "text_with_cta":     edited.get("improved_text", ""),
                "saved_path":        "",
            }

        # ── Stage 6: Approval packet ──────────────────────────────────────────
        print(f"  [stage 6/{platform}] Building approval packet…")
        try:
            packet = self.approver.create_packet(
                topic        = topic,
                platform     = platform,
                hook_result  = hook_result,
                line_result  = edited,
                monetization = monetization,
                draft        = draft,
                brief        = brief,
            )
            artifacts["final"]   = packet.get("final_artifact_path", "")
            artifacts["packet"]  = packet.get("packet_path", "")
            print(f"    overall score: {packet.get('overall_score', 0):.1f} | status: {packet.get('status', '?')}")
        except Exception as exc:
            errors.append(f"ApprovalAgent: {exc}")
            traceback.print_exc()
            packet = {
                "approval_id":        run_id,
                "status":             "error",
                "overall_score":      0.0,
                "scores":             {},
                "hook":               hook_result.get("best_hook", {}).get("hook", ""),
                "word_count":         draft.get("word_count", 0),
                "primary_cta":        "",
                "monetization_paths": [],
                "artifacts":          artifacts,
                "final_artifact_path": "",
                "packet_path":        "",
            }

        # ── Stage 7: Discord delivery ─────────────────────────────────────────
        print(f"  [stage 7/{platform}] Delivering to Discord…")
        discord_ok = _discord_deliver(packet, topic, platform)
        print(f"    discord: {'✅ sent' if discord_ok else '⚠️ skipped/failed'}")

        # ── Stage 8: Supabase workflow_output ────────────────────────────────
        wf_row = {
            "id":           str(uuid.uuid4()),
            "created_at":   _now_iso(),
            "workflow_type": "content_pipeline",
            "topic":        topic,
            "platform":     platform,
            "approval_id":  packet.get("approval_id", run_id),
            "status":       packet.get("status", "error"),
            "overall_score": packet.get("overall_score", 0),
            "hook":         packet.get("hook", ""),
            "word_count":   packet.get("word_count", 0),
            "primary_cta":  packet.get("primary_cta", ""),
            "artifacts":    json.dumps(artifacts, default=str),
            "errors":       json.dumps(errors),
            "discord_sent": discord_ok,
        }
        workflow_id = _save_workflow_output(wf_row)
        if workflow_id:
            print(f"    workflow_output id: {workflow_id}")

        return {
            "platform":     platform,
            "run_id":       run_id,
            "draft":        draft,
            "edited":       edited,
            "monetization": monetization,
            "packet":       packet,
            "artifacts":    artifacts,
            "discord_sent": discord_ok,
            "workflow_id":  workflow_id,
            "errors":       errors,
        }

    # ── public ────────────────────────────────────────────────────────────────

    def run(
        self,
        topic: str,
        platforms: list[str] | None = None,
        max_hook_retries: int = 2,
    ) -> dict:
        """
        Run the full content pipeline for topic across all platforms.

        Returns a summary dict with per-platform results and all artifacts.
        Raises RuntimeError only if the research stage fails (no brief = nothing else can run).
        """
        if not platforms:
            platforms = ["youtube", "newsletter"]

        print(f"\n[pipeline] Starting content pipeline")
        print(f"  topic:     {topic[:100]}")
        print(f"  platforms: {', '.join(platforms)}")
        print(f"  time:      {_now_iso()}\n")

        results: dict[str, Any] = {
            "topic":       topic,
            "platforms":   platforms,
            "started_at":  _now_iso(),
            "brief":       {},
            "hooks":       [],
            "hook_report": {},
            "per_platform": {},
            "errors":      [],
        }

        # ── Stage 1: Research ────────────────────────────────────────────────
        print("[stage 1] ResearchAgent sweep…")
        try:
            brief = self.research.sweep(topic, platform=platforms[0])
            results["brief"] = brief
            print(f"  brief saved → {brief.get('saved_path', 'N/A')}")
        except Exception as exc:
            results["errors"].append(f"ResearchAgent: {exc}")
            traceback.print_exc()
            raise RuntimeError(f"Research stage failed — cannot continue: {exc}") from exc

        # ── Stage 2: Hooks ───────────────────────────────────────────────────
        print("\n[stage 2a] HookAgent generating 10 hooks…")
        best_hook_result: dict = {}
        for attempt in range(1, max_hook_retries + 2):
            try:
                hooks = self.hooks.generate(topic, brief, n=10)
                results["hooks"] = hooks
                print(f"  generated {len(hooks)} hooks (attempt {attempt})")
            except Exception as exc:
                results["errors"].append(f"HookAgent attempt {attempt}: {exc}")
                traceback.print_exc()
                hooks = []

            print(f"[stage 2b] HookGatekeeper scoring (attempt {attempt})…")
            try:
                hook_report = self.gatekeeper.score(hooks, topic, brief)
                results["hook_report"] = hook_report
                best_hook_result       = hook_report
                _scored = hook_report.get("scored_hooks", [])
                _best_score = _scored[0].get("average", 0) if _scored else 0
                print(f"  passing: {hook_report.get('passing_count', 0)} | best score: {_best_score:.2f}")
                print(f"  hook report → {hook_report.get('saved_path', 'N/A')}")
                if hook_report.get("passed"):
                    break
                print(f"  No hooks above threshold — retrying…")
            except Exception as exc:
                results["errors"].append(f"HookGatekeeper attempt {attempt}: {exc}")
                traceback.print_exc()

        if not best_hook_result:
            best_hook_result = {
                "best_hook":     {"hook": topic, "avg_score": 0},
                "passed":        False,
                "passing_count": 0,
                "saved_path":    "",
            }

        # ── Stages 3–7: Per platform ─────────────────────────────────────────
        for platform in platforms:
            print(f"\n[pipeline] ── Platform: {platform.upper()} ──────────────")
            try:
                pr = self._run_platform(topic, platform, brief, best_hook_result)
                results["per_platform"][platform] = pr
            except Exception as exc:
                results["errors"].append(f"platform/{platform}: {exc}")
                traceback.print_exc()
                results["per_platform"][platform] = {
                    "platform": platform,
                    "errors":   [str(exc)],
                    "packet":   {"status": "error", "overall_score": 0},
                    "artifacts": {},
                    "discord_sent": False,
                }

        results["finished_at"] = _now_iso()

        # ── Final summary ────────────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("[pipeline] COMPLETE")
        print(f"  topic:    {topic[:80]}")
        for pl, pr in results["per_platform"].items():
            packet = pr.get("packet", {})
            status = packet.get("status", "error")
            score  = packet.get("overall_score", 0)
            emoji  = "✅" if status == "approval_ready" else "⚠️"
            print(f"  {pl:12s} {emoji} {status:18s} score={score:.1f}")
            for aname, apath in pr.get("artifacts", {}).items():
                if apath:
                    print(f"             └─ {aname}: {Path(str(apath)).name}")
        if results["errors"]:
            print(f"\n  errors ({len(results['errors'])}):")
            for e in results["errors"]:
                print(f"    • {e}")
        print("=" * 60 + "\n")

        return results
