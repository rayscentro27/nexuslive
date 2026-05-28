"""
hermes_agent_handoff_builder.py
=================================
Build structured handoff prompts for Claude Code, Codex, Gemini CLI, and OpenCode.

Every handoff must:
  - Name the originating source (intake_id / dispatch_id / URL)
  - Name the target agent
  - Specify the exact task in one sentence
  - List acceptance criteria (what artifacts must exist when done)
  - Include the compliance contract (NO ARTIFACT = NO COMPLETION)
  - Never claim completion without verified artifact paths
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

ROOT         = Path(__file__).resolve().parent.parent
HANDOFF_DIR  = ROOT / "docs" / "reports" / "agent_handoffs"

AgentTarget  = Literal["claude_code", "codex", "gemini", "opencode", "hermes"]


class AgentHandoff:
    """Structured prompt package for a dev-agent handoff."""

    def __init__(self, data: dict):
        self._data = data

    @property
    def handoff_id(self) -> str:
        return self._data["handoff_id"]

    @property
    def target_agent(self) -> str:
        return self._data["target_agent"]

    @property
    def prompt(self) -> str:
        return self._data["prompt"]

    @property
    def file_path(self) -> str:
        return self._data.get("file_path", "")

    def to_dict(self) -> dict:
        return dict(self._data)

    def telegram_summary(self) -> str:
        d = self._data
        return (
            f"📋 *Agent Handoff Created*\n"
            f"ID: `{d['handoff_id']}`\n"
            f"Target: {d['target_agent']}\n"
            f"Task: {d['task_summary']}\n"
            f"Artifact: `{d.get('file_path', 'pending')}`"
        )


class HermesAgentHandoffBuilder:
    """
    Build and persist structured handoff documents for CLI dev agents.

    Every handoff:
      - Has a unique ID
      - Names the originating source
      - Defines the task in one sentence
      - Lists required acceptance artifacts
      - Embeds the NO ARTIFACT = NO COMPLETION contract
    """

    def build(
        self,
        target_agent: AgentTarget,
        task_summary: str,
        task_detail: str,
        acceptance_criteria: list[str],
        source_url: str = "",
        source_type: str = "",
        intake_id: str = "",
        dispatch_id: str = "",
        context_files: list[str] | None = None,
        priority: str = "medium",
        submitted_by: str = "raymond",
    ) -> AgentHandoff:
        """Build and persist a handoff for a dev agent."""
        handoff_id  = "hnd_" + uuid.uuid4().hex[:12]
        ts          = datetime.now(timezone.utc).isoformat()
        prompt      = self._render_prompt(
            handoff_id=handoff_id,
            target_agent=target_agent,
            task_summary=task_summary,
            task_detail=task_detail,
            acceptance_criteria=acceptance_criteria,
            source_url=source_url,
            source_type=source_type,
            intake_id=intake_id,
            dispatch_id=dispatch_id,
            context_files=context_files or [],
        )
        file_path   = self._save(handoff_id, prompt)

        record = {
            "handoff_id":          handoff_id,
            "target_agent":        target_agent,
            "task_summary":        task_summary,
            "priority":            priority,
            "source_url":          source_url,
            "source_type":         source_type,
            "intake_id":           intake_id,
            "dispatch_id":         dispatch_id,
            "acceptance_criteria": acceptance_criteria,
            "context_files":       context_files or [],
            "prompt":              prompt,
            "file_path":           file_path,
            "submitted_by":        submitted_by,
            "created_at":          ts,
            "status":              "pending",
        }

        self._log(record)
        self._register_artifact(record)
        return AgentHandoff(record)

    def build_youtube_handoff(
        self,
        source_id: str,
        url: str,
        title: str = "",
        intake_id: str = "",
    ) -> AgentHandoff:
        """Build a standard YouTube research handoff for claude_code."""
        return self.build(
            target_agent="claude_code",
            task_summary=f"Run YouTube intelligence cycle for: {url}",
            task_detail=(
                f"Process the YouTube source `{url}` through the full intelligence pipeline.\n\n"
                f"Steps:\n"
                f"1. Run `python scripts/run_youtube_intelligence_cycle.py --source-id {source_id}`\n"
                f"2. Verify output artifacts exist in docs/reports/youtube/\n"
                f"3. Register all output artifacts in nexus_artifact_registry.jsonl\n"
                f"4. Update source registry status to 'research_complete'\n"
                f"5. Notify Hermes via hermes_proactive_notifier when done"
            ),
            acceptance_criteria=[
                f"docs/reports/youtube/content_intelligence_{source_id}_*.json exists",
                f"docs/reports/youtube/youtube_intelligence_report_{source_id}_*.md exists",
                f"nexus_artifact_registry.jsonl has entry for source_id={source_id}",
                f"youtube_source_registry.json shows status=research_complete for {source_id}",
            ],
            source_url=url,
            source_type="youtube_video",
            intake_id=intake_id,
            priority="medium",
        )

    def build_github_handoff(
        self,
        repo_url: str,
        intake_id: str = "",
    ) -> AgentHandoff:
        """Build a GitHub trend research handoff."""
        return self.build(
            target_agent="claude_code",
            task_summary=f"Run GitHub repo intelligence review for: {repo_url}",
            task_detail=(
                f"Review the GitHub repository `{repo_url}` for Nexus improvement signals.\n\n"
                f"Steps:\n"
                f"1. Run `python scripts/run_weekly_github_trend_research.py --repo {repo_url}`\n"
                f"2. Produce a report in docs/reports/github_trends/\n"
                f"3. Register all outputs in nexus_artifact_registry.jsonl\n"
                f"4. Flag any patterns that could improve Nexus architecture"
            ),
            acceptance_criteria=[
                f"docs/reports/github_trends/ contains new report for {repo_url}",
                "nexus_artifact_registry.jsonl updated with new entry",
            ],
            source_url=repo_url,
            source_type="github_repo",
            intake_id=intake_id,
            priority="low",
        )

    def build_code_task_handoff(
        self,
        task_description: str,
        target_files: list[str],
        target_agent: AgentTarget = "claude_code",
        intake_id: str = "",
    ) -> AgentHandoff:
        """Build a code implementation handoff."""
        return self.build(
            target_agent=target_agent,
            task_summary=task_description[:120],
            task_detail=(
                f"Implement the following task:\n\n{task_description}\n\n"
                f"Target files:\n" + "\n".join(f"  - {f}" for f in target_files) + "\n\n"
                f"IMPORTANT:\n"
                f"  - Do NOT enable live trading\n"
                f"  - Do NOT connect real broker accounts\n"
                f"  - Do NOT publish content publicly\n"
                f"  - Do NOT spend money\n"
                f"  - All changes must be reversible\n"
                f"  - Register output artifacts before reporting complete"
            ),
            acceptance_criteria=[
                "All modified files pass python -m py_compile",
                "No new security vulnerabilities introduced",
                "nexus_artifact_registry.jsonl updated with task output",
                "Ray approval obtained before any live deployment",
            ],
            source_type="code_task",
            intake_id=intake_id,
            priority="high",
        )

    # ── Internals ──────────────────────────────────────────────────────────────

    def _render_prompt(
        self,
        handoff_id: str,
        target_agent: str,
        task_summary: str,
        task_detail: str,
        acceptance_criteria: list[str],
        source_url: str,
        source_type: str,
        intake_id: str,
        dispatch_id: str,
        context_files: list[str],
    ) -> str:
        criteria_block = "\n".join(f"  - [ ] {c}" for c in acceptance_criteria)
        context_block  = "\n".join(f"  - {f}" for f in context_files) if context_files else "  (none)"
        return f"""# Nexus Agent Handoff
*Handoff ID: {handoff_id}*
*Target Agent: {target_agent}*
*Created: {datetime.now(timezone.utc).isoformat()}*

## Task Summary
{task_summary}

## Task Detail
{task_detail}

## Source
- **URL:** {source_url or '(no URL)'}
- **Type:** {source_type or '(unknown)'}
- **Intake ID:** {intake_id or '(none)'}
- **Dispatch ID:** {dispatch_id or '(none)'}

## Context Files
{context_block}

## Acceptance Criteria
{criteria_block}

## Compliance Contract
⚠️ **NO ARTIFACT = NO COMPLETION.**
- Every output file must exist on disk before marking this task complete.
- Every output must be registered in `nexus_artifact_registry.jsonl`.
- Do NOT claim completion without verified artifact paths.
- Do NOT enable live trading, connect real brokers, or publish client-facing content.
- Do NOT spend money or call paid APIs without Ray's approval.
- All changes must be reviewed by Ray before deployment.

## How to run (copy-paste)
```
# Start this handoff:
cat {handoff_id}.md | pbcopy   # paste into {target_agent}
# Or:
{target_agent} < {handoff_id}.md
```
"""

    def _save(self, handoff_id: str, prompt: str) -> str:
        HANDOFF_DIR.mkdir(parents=True, exist_ok=True)
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = HANDOFF_DIR / f"agent_handoff_{handoff_id}_{ts}.md"
        path.write_text(prompt)
        return str(path)

    def _log(self, record: dict) -> None:
        HANDOFF_DIR.mkdir(parents=True, exist_ok=True)
        log = HANDOFF_DIR / "agent_handoff_log.jsonl"
        entry = {k: v for k, v in record.items() if k != "prompt"}
        with log.open("a") as f:
            f.write(json.dumps(entry) + "\n")

    def _register_artifact(self, record: dict) -> None:
        try:
            from lib.nexus_artifact_registry import register_artifact
            register_artifact(
                agent_name="hermes_agent_handoff_builder",
                agent_type="hermes",
                source_input=record.get("source_url", ""),
                source_type=record.get("source_type", "other"),
                artifact_type="prompt",
                title=f"Agent handoff: {record['task_summary'][:60]}",
                summary=f"Handoff for {record['target_agent']} — {record['task_summary'][:80]}",
                file_path=record.get("file_path", ""),
                tags=["agent_handoff", record["target_agent"]],
                what_hermes_should_know=(
                    f"A handoff was created for {record['target_agent']}. "
                    f"Task: {record['task_summary']}. "
                    f"Status: pending Ray review."
                ),
                next_action=f"Open {record.get('file_path', '')} and run in {record['target_agent']}",
            )
        except Exception:
            pass

    def pending_handoffs(self) -> list[AgentHandoff]:
        log = HANDOFF_DIR / "agent_handoff_log.jsonl"
        if not log.exists():
            return []
        results = []
        for line in log.read_text().splitlines():
            line = line.strip()
            if line:
                try:
                    d = json.loads(line)
                    if d.get("status") == "pending":
                        results.append(AgentHandoff(d))
                except Exception:
                    pass
        return results


# ── Singleton ─────────────────────────────────────────────────────────────────
_builder = HermesAgentHandoffBuilder()


def build_handoff(
    target_agent: AgentTarget,
    task_summary: str,
    task_detail: str,
    acceptance_criteria: list[str],
    **kwargs,
) -> AgentHandoff:
    return _builder.build(
        target_agent=target_agent,
        task_summary=task_summary,
        task_detail=task_detail,
        acceptance_criteria=acceptance_criteria,
        **kwargs,
    )


def build_youtube_handoff(source_id: str, url: str, **kwargs) -> AgentHandoff:
    return _builder.build_youtube_handoff(source_id=source_id, url=url, **kwargs)


def build_github_handoff(repo_url: str, **kwargs) -> AgentHandoff:
    return _builder.build_github_handoff(repo_url=repo_url, **kwargs)


def build_code_task_handoff(task_description: str, target_files: list[str], **kwargs) -> AgentHandoff:
    return _builder.build_code_task_handoff(
        task_description=task_description,
        target_files=target_files,
        **kwargs,
    )


def pending_handoffs() -> list[AgentHandoff]:
    return _builder.pending_handoffs()
