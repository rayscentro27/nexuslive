"""
intake.py — Normalize inbound messages from any source into a unified command object.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Literal

Source  = Literal["email", "telegram", "cli"]
Priority = Literal["critical", "high", "medium", "low"]


def normalize(
    raw_text: str,
    source: Source = "cli",
    sender: str = "raymond",
    message_id: str = "",
    reply_channel: str = "",
) -> dict:
    """Return a normalized command object."""
    now = datetime.now(timezone.utc).isoformat()
    mid = message_id or f"cmd-{uuid.uuid4().hex[:12]}"
    dedupe_key = hashlib.sha256(f"{source}:{sender}:{raw_text[:200]}".encode()).hexdigest()[:32]

    intent, priority, requires_approval = classify_intent(raw_text)

    return {
        "command_id":              mid,
        "source":                  source,
        "raw_text":                raw_text,
        "sender":                  sender,
        "received_at":             now,
        "message_id":              mid,
        "dedupe_key":              dedupe_key,
        "intent":                  intent,
        "priority":                priority,
        "status":                  "pending",
        "reply_channel":           reply_channel or source,
        "requires_human_approval": requires_approval,
    }


# Deterministic intent classification — no AI needed for common commands.
# IMPORTANT: higher-priority special phrases are checked first.
_INTENT_MAP: list[tuple[list[str], str, Priority, bool]] = [
    # (keywords, intent, priority, requires_approval)

    # ── Dev Agent Bridge (must appear BEFORE generic keyword catches) ───────────
    (["list dev agents", "which coding agents", "coding agents available",
      "what agents", "dev agents", "available agents", "agent bridge",
      "run dev agent status"],                                "list_dev_agents",           "low",    False),

    (["ask gemini", "prepare a prompt for gemini",
      "use gemini", "gemini review", "gemini analyze",
      "ask opencode", "prepare a prompt for opencode",
      "use opencode", "opencode implement",
      "ask claude cli", "prepare a prompt for claude",
      "claude cli review",
      "ask codex", "prepare a prompt for codex",
      "use codex", "codex patch"],                            "prepare_dev_handoff",       "medium", True),

    (["recommend agent", "which agent should", "what agent should",
      "best agent for", "which cli agent", "suggest agent",
      "which coding agent"],                                  "recommend_dev_agent",       "low",    False),

    # ── Small talk / greetings (must be BEFORE any generic keyword catches) ────
    (["did you get enough sleep", "did you sleep", "do you sleep",
      "did you rest", "are you rested",
      "how are you", "how are you doing", "how you doing",
      "are you awake", "are you online", "you good",
      "good morning", "good afternoon", "good evening",
      "good night", "hey hermes", "hi hermes",
      "you there", "you still there"],                         "small_talk",                "low",    False),

    # ── Date / time questions ─────────────────────────────────────────────────
    (["what is today's date", "what is todays date", "what's today's date",
      "what's todays date", "what day is it", "what day is today",
      "what is the date", "what's the date", "today's date",
      "what time is it", "what is the time", "current date",
      "what is today"],                                        "date_time_question",        "low",    False),

    # ── Tomorrow / planning questions ─────────────────────────────────────────
    (["what do you have planned for tomorrow", "what are we doing tomorrow",
      "what should we work on tomorrow", "tomorrow plan",
      "plan for tomorrow", "what's planned for tomorrow",
      "what is planned for tomorrow", "what's the plan for tomorrow",
      "tomorrows plan", "tomorrow's plan"],                    "tomorrow_plan",             "low",    False),

    # ── Unknown-handling / policy questions ───────────────────────────────────
    (["what if you don't know", "what if you dont know",
      "what if you dont have the answer", "what if you don't have the answer",
      "what if you cannot answer", "what if you can't answer",
      "what happens if you don't know", "what happens if you dont know",
      "how do you handle unknowns", "how do you handle not knowing",
      "what do you do when you don't know",
      "what do you do when you dont know"],                    "unknown_handling",          "low",    False),

    # ── Special phrases (must be before generic keyword catches) ────────────────
    (["are we ready", "ready for pilot", "10-user pilot", "10 user pilot",
      "pilot ready", "pilot launch", "ready to launch", "ready for launch"],
                                                           "pilot_readiness",           "high",   False),

    # ── Phase 6B: last plan (must be BEFORE daily_operating_cycle — "daily plan" keyword collision) ──
    (["show last daily plan", "show last plan", "what was the last plan",
      "show previous plan", "what was yesterday's plan",
      "show me the last daily plan", "what was the last daily plan",
      "last nexus plan", "previous daily plan",
      "show the last plan", "what did the last plan say"],            "show_last_daily_plan",       "high",   False),

    # ── Daily operating cycle (must be BEFORE next_best_move and business_opportunities) ──
    (["run daily operating cycle", "hermes run daily operating cycle",
      "hermes, run daily operating cycle",
      "daily operating cycle", "run daily cycle",
      "what should i work on today", "what should we work on today",
      "what should i focus on today", "what should we focus on today",
      "show today's nexus plan", "show today's plan",
      "show today nexus plan", "nexus plan today",
      "today's nexus plan", "todays nexus plan",
      "todays plan",
      "show nexus plan", "daily plan"],                              "daily_operating_cycle",     "high",   False),

    # Redirected to Phase 6C show_approval_queue (replaces old daily_approval_needed keywords)
    (["show approval queue", "show items needing approval",
      "approval queue", "what is waiting for my approval",
      "show approval needed", "what needs ray approval",
      "show what needs approval",
      "what needs my approval", "pending approvals",
      "approval needed", "what is waiting for approval",
      "what requires approval", "what is pending approval"],         "show_approval_queue",        "high",   False),

    (["continue while i am out", "continue while i'm out",
      "keep working while i am out", "keep working while i'm out",
      "what can you do while i am gone", "what can you do while i'm gone",
      "what can you do while i am away", "work while i am out",
      "keep going while i am out", "continue work",
      "continue while i am gone", "work while i am away"],           "daily_continue_while_out",   "medium", False),

    # ── 30-day revenue plan (must be BEFORE daily_top_revenue_move and business_opportunities) ──
    (["30 day revenue plan", "30-day revenue plan",
      "plan to make money this month", "how do we make money this month",
      "make money in the next 30 days", "30 day plan",
      "get to 1000 a week", "get to $1000 a week",
      "how do we get to 1000 a week", "how to make 1000 a week",
      "revenue plan for the month", "monthly revenue plan",
      "we need to come up with a plan to make money"],               "thirty_day_revenue_plan",    "high",   False),

    (["show today's top revenue move", "show today's top money move",
      "top revenue move", "top money move today",
      "best revenue move today", "what is the top revenue move",
      "today's top money move", "today's top revenue move",
      "show top money move", "show revenue move",
      "what can make money today", "how do we make money today",
      "todays top revenue move", "todays top money move"],           "daily_top_revenue_move",     "high",   False),

    (["show today's blockers", "show blockers", "what is blocked",
      "what is stopping us", "show current blockers",
      "what are the blockers", "today's blockers",
      "current blockers", "what's blocked",
      "blockers today", "todays blockers"],                          "daily_blockers",              "high",   False),

    # ── Phase 6B: daily cycle state commands ─────────────────────────────────
    (["what did you do while i was out", "what happened while i was out",
      "while i was out", "while i was away", "while i was gone",
      "what did hermes do while i was out", "catch me up from last plan",
      "what have you been doing", "what did you get done",
      "while you were running", "what did you work on"],              "while_out_summary",          "high",   False),

    (["show pending items", "what is pending", "pending cycle items",
      "what needs doing", "show what is pending", "list pending items",
      "pending daily items", "what items are pending",
      "show pending daily items", "pending tasks",
      "what still needs to be done", "what needs attention",
      # phrases with "still pending" / "pending from today" / "left from today"
      "still pending", "pending from today",
      "what is still pending", "what's still pending", "whats still pending",
      "what is left from today", "what is left to do",
      "what still needs to be done today", "what is unfinished from today",
      "what is still open today", "what is still open",
      "unfinished from today", "what is still left"],                "pending_daily_items",        "high",   False),

    (["compare since last plan", "what changed since last plan",
      "what is new since the last plan", "compare to last plan",
      "what changed since yesterday", "what's new since the plan",
      "what changed", "how has the plan changed",
      "compare current plan", "plan comparison",
      "what is different since last time"],                           "compare_since_last_plan",    "high",   False),

    (["mark complete", "mark as complete", "mark done", "mark as done",
      "mark item complete", "mark item done",
      "mark daily item complete", "mark daily item done",
      "complete daily item", "complete item",
      "that is complete", "mark that complete",
      "mark it complete", "mark it done",
      "completed that", "finished that item"],                        "mark_daily_item_complete",   "high",   True),

    # ── Phase 6C: Approval queue (must be BEFORE handoff_check — "approval required" keyword collision) ──
    (["show approval queue", "approval queue",
      "what needs my approval", "what needs approval",
      "show pending approvals", "pending approvals",
      "approval needed", "what approvals are pending",
      "show items needing approval", "items needing approval",
      "list approval items", "list approvals",
      "what is in the approval queue"],                              "show_approval_queue",        "high",   False),

    (["show approval item", "approval item detail",
      "tell me about approval item", "details for approval item",
      "what is approval item", "describe approval item",
      "approval item info", "explain approval item"],               "show_approval_item",         "high",   False),

    # approval_impact must be BEFORE approve_item/reject_item — "approve item" is a substring
    (["what happens if i approve", "what would happen if i approve",
      "if i approve item", "impact of approving",
      "if approved item", "simulate approval",
      "what happens if i reject", "if i reject item",
      "impact of rejecting", "if rejected item",
      "simulate rejection"],                                        "approval_impact",            "high",   False),

    (["approve item", "approve this item", "i approve item",
      "give approval for item", "approved item",
      "yes approve item", "approve number"],                        "approve_item",               "high",   True),

    (["reject item", "reject this item", "i reject item",
      "do not approve item", "deny item",
      "rejected item", "decline item"],                             "reject_item",                "high",   True),

    (["clear stale approvals", "clean up stale approvals",
      "archive old approvals", "remove stale approvals",
      "stale approval cleanup", "clear old approvals",
      "cleanup stale approvals"],                                   "clear_stale_approvals",      "medium", False),

    (["bulk approve", "approve all safe items",
      "approve blocked internal items", "approve all internal items",
      "bulk approve blocked", "approve safe items"],                "bulk_approve_blocked",       "high",   True),

    # ── Phase 7 + 7A: CFO conversation / research queue (BEFORE Phase 6F to avoid collisions) ──
    # dedupe_research_queue MUST come before show_research_queue (contains "research queue")
    (["dedupe research queue", "deduplicate research queue",
      "clean research queue", "remove duplicate research questions",
      "remove duplicates from research queue"],                       "dedupe_research_queue",        "medium", False),

    (["show research queue", "research queue",
      "show open research questions", "what is in the research queue",
      "what questions are open", "show pending research"],            "show_research_queue",         "medium", False),

    (["show scout assignments", "scout assignments",
      "what are scouts working on", "active scout assignments",
      "show active scouts"],                                          "show_scout_assignments",       "medium", False),

    (["what did the scouts find", "what did scouts find",
      "what did you find", "scout findings", "show scout results",
      "what have scouts discovered"],                                 "show_scout_assignments",       "medium", False),

    (["what are you still trying to figure out", "what are you figuring out",
      "show unresolved questions", "unresolved questions",
      "what don't you know", "what do you not know yet",
      "show unknown questions", "what can't you answer"],            "show_unresolved_questions",    "medium", False),

    (["create prompt from this", "create a prompt from this",
      "turn this into a claude prompt", "turn this into a prompt",
      "create implementation prompt", "give me a prompt for claude",
      "what should i send claude", "create a super prompt",
      "have opencode fix this", "make an implementation prompt"],    "create_implementation_prompt", "high",   True),

    (["show last strategic decision", "last strategic decision",
      "show cfo notes", "cfo notes", "what did hermes decide",
      "show strategic decisions"],                                    "show_cfo_notes",               "medium", False),

    (["save this as a decision", "save as decision",
      "record this decision", "save this decision"],                  "save_cfo_decision",            "medium", True),

    (["add this to the research queue", "add to research queue",
      "add this question to research", "put this in the research queue"],
                                                                      "show_research_queue",          "medium", True),

    # ── Phase 6F: Revenue asset fixer (BEFORE Phase 6E/6D to avoid substring collisions) ──
    (["fix revenue packet assets", "apply safe asset fixes",
      "fix packet gaps", "fix revenue asset gaps",
      "clean revenue assets", "fix revenue assets",
      "apply internal fixes", "fix content assets"],               "fix_revenue_packet_assets",   "high",  False),

    (["remove unsafe promises from assets", "soften unsafe language",
      "fix unsafe promise language", "remove guarantees from assets",
      "fix promise language"],                                     "fix_revenue_packet_assets",   "high",  False),

    (["add cta to revenue assets", "add cta to assets",
      "add call to action to assets"],                             "fix_revenue_packet_assets",   "high",  False),

    (["add compliance notes to assets", "add compliance note to assets",
      "add disclaimer to assets", "add compliance notes"],        "fix_revenue_packet_assets",   "high",  False),

    (["show asset fix report", "asset fix report",
      "show fix report", "what was fixed",
      "show what was fixed", "asset repair report"],              "show_asset_fix_report",       "medium", False),

    (["rescore after fixes", "rescore packet after fixes",
      "update score after fixes", "refresh score after fixes",
      "what is the score after fixes"],                           "rescore_after_fixes",         "high",  False),

    # ── Phase 6E: Revenue packet improvement (BEFORE Phase 6D to avoid substring collisions) ──
    (["show revenue packet gaps", "show readiness gaps",
      "revenue packet gaps", "what are the packet gaps",
      "show packet gaps", "packet readiness gaps",
      "what gaps does the revenue packet have"],                    "show_revenue_packet_gaps",    "high",   False),

    (["improve revenue asset packet", "improve the revenue packet",
      "improve packet score", "raise packet readiness",
      "improve readiness score", "fix revenue packet",
      "raise revenue packet score"],                               "improve_revenue_asset_packet", "high",  False),

    (["show improved cta options", "show improved cta",
      "improved cta options", "improved cta set",
      "show enhanced cta", "show all cta options"],                "show_improved_cta_options",   "medium", False),

    (["show offer bridge", "offer bridge",
      "show the offer bridge", "what is the offer bridge",
      "show funnel model", "funnel model",
      "free to paid funnel"],                                      "show_offer_bridge",           "medium", False),

    (["show packet improvement plan", "packet improvement plan",
      "show improvement plan", "what is the improvement plan",
      "revenue packet plan", "improvement roadmap"],               "show_packet_improvement_plan", "high",  False),

    (["rescore revenue packet", "rescore the revenue packet",
      "refresh revenue packet score", "rescore packet",
      "recalculate packet score", "update packet score"],          "rescore_revenue_packet",      "high",   False),

    (["show final review checklist", "final review checklist",
      "final checklist", "pre-launch final checklist",
      "show pre-launch review", "final pre-launch checklist"],     "show_final_review_checklist", "high",   False),

    # ── Phase 6D: Revenue asset packet ───────────────────────────────────────
    (["build revenue asset packet", "create revenue asset packet",
      "generate revenue asset packet", "build revenue packet",
      "create revenue packet"],                                     "build_revenue_asset_packet", "high",   False),

    (["show revenue asset packet", "show latest revenue packet",
      "show revenue packet", "revenue asset packet",
      "revenue packet status", "show the revenue packet",
      "what is in the revenue packet"],                             "show_revenue_asset_packet",  "high",   False),

    (["show launch-ready assets", "show launch ready assets",
      "launch ready assets", "what assets are launch ready",
      "what is launch ready", "show ready assets"],                 "show_launch_ready_assets",   "high",   False),

    (["show content awaiting approval", "content awaiting approval",
      "what content needs approval", "show content pending approval",
      "content pending review", "what is awaiting approval"],       "show_content_awaiting_approval", "high", False),

    (["show cta options", "show cta", "cta options",
      "what are the cta options", "show call to action",
      "cta copy options"],                                          "show_cta_options",           "medium", False),

    (["show launch checklist", "launch checklist",
      "show the launch checklist", "what is on the launch checklist",
      "pre-launch checklist", "pre launch checklist"],              "show_launch_checklist",      "medium", False),

    (["show approval checklist", "approval checklist",
      "show the approval checklist", "what is on the approval checklist"],
                                                                    "show_approval_checklist",    "medium", False),

    (["generate approval candidates", "create approval candidates",
      "create approval items from packet", "generate approval items",
      "create approval queue items from packet",
      "generate candidates from packet"],                           "generate_approval_candidates", "high", False),

    (["next best move", "what should we do", "what's the next",
      "what is the next step", "what do you recommend", "recommend",
      "best move", "next move", "what now"],               "next_best_move",            "high",   False),

    # ── Strategic operating partner (must be BEFORE generic keyword catches) ────
    (["catch me up", "where are we", "are we on track",
      "what did nexus produce", "what happened since",
      "nexus status", "what's the nexus status"],                   "nexus_status",              "high",   False),

    (["pending handoff",
      "waiting on me", "show handoffs", "what do you need",
      "need my sign", "approval required",
      "needs approval", "what is pending my"],                      "handoff_check",             "high",   False),

    (["what evidence do you have", "show verified status",
      "show me verified", "verified status only",
      "what is verified", "show evidence",
      "evidence only", "what artifacts do you have"],               "nexus_status",              "high",   False),

    (["what youtube videos did i send", "what youtube did i send today",
      "youtube videos today", "which youtube did i send",
      "what links did i send today", "what videos did i send"],     "source_intake_status",      "medium", False),

    (["what happened to the last link", "last link i sent",
      "what did you do with the link", "did you process the link",
      "what happened to the link i sent"],                          "source_intake_status",      "medium", False),

    (["hermes decided", "decision log", "what did hermes decide",
      "autonomous decision", "hermes own decision"],                "decision_log",              "medium", False),

    (["demo order", "oanda demo", "demo broker",
      "demo trade", "last trade demo", "practice order"],           "demo_broker_status",        "medium", False),

    (["beehiiv", "beehive", "bee hive", "bee-hive", "behive", "behiiv",
      "newsletter alternative", "newsletter platform",
      "email platform alternative", "newsletter tool alternative",
      "premium blocker",
      "free alternative", "replace beehiiv",
      "cheap alternative", "tool blocker"],                         "premium_blocker_resolver",  "low",    False),

    # ── Learning loop commands (must be BEFORE save_ray_feedback) ──────────────
    (["record this lesson:", "remember this lesson:", "learn this:",
      "use this lesson next time:", "save this as a lesson:",
      "add lesson:", "note this lesson:", "store this lesson:",
      "lesson:"],                                                     "lesson_record",             "low",    False),

    (["show pending lessons", "list pending lessons",
      "what lessons are pending", "pending lesson proposals",
      "show lesson proposals", "lessons pending review"],             "lesson_pending",            "low",    False),

    (["show active lessons", "list active lessons",
      "what lessons are active", "active lessons in memory",
      "show lessons in memory", "what lessons did hermes learn"],     "lesson_active",             "low",    False),

    # ── Bulk lesson approval (must be BEFORE lesson_approve) ────────────────────
    (["approve all", "approve these lessons", "approve pending lessons",
      "approve the pending lessons"],                                  "lesson_approve_all",        "low",    False),

    (["approve lesson", "i approve lesson"],                          "lesson_approve",            "low",    False),

    (["reject lesson", "i reject lesson"],                            "lesson_reject",             "low",    False),

    (["deprecate lesson", "remove lesson"],                           "lesson_deprecate",          "low",    False),

    (["what did you learn from that", "what lesson did you learn",
      "what did hermes learn", "what lesson came from that",
      "show last lesson proposal", "last lesson"],                    "lesson_learned",            "low",    False),

    (["where did that lesson come from", "why did you use that memory",
      "lesson source", "explain lesson", "lesson traceability",
      "where does that lesson come from",
      "what is the source of that lesson"],                           "lesson_source",             "low",    False),

    (["generate gap lessons", "create lessons from gaps",
      "turn gaps into lessons", "convert gaps to lessons"],           "lesson_gap_generate",       "low",    False),

    (["record lesson", "remember this", "save feedback",
      "save lesson", "note this", "log lesson"],                      "save_ray_feedback",         "low",    False),

    (["notification log", "telegram notification",
      "what did hermes send", "hermes notification",
      "notification sent", "proactive notification"],               "notification_log",          "low",    False),

    (["can you hear me", "test communication", "hello hermes",
      "are you there", "is this working", "comm check", "comms check",
      "communication test", "ping"],                       "communication_health",      "medium", False),

    # ── Knowledge gap review commands (before generic research entry) ──────────
    (["show knowledge gaps", "show unanswered questions",
      "what could you not answer", "show gaps",
      "what questions were unanswered", "show unanswered",
      "what did you not know", "what gaps do you have",
      "hermes show knowledge gaps"],                                   "knowledge_gap_review",        "low",    False),

    (["research unanswered", "create better answers for gaps",
      "research knowledge gaps", "improve gap answers",
      "fix knowledge gaps", "resolve knowledge gaps",
      "create gap research tasks", "improve hermes answers",
      "unanswered questions research"],                               "knowledge_gap_research",      "low",    True),

    (["archive resolved gaps", "clear resolved gaps",
      "archive old gaps", "mark gaps resolved"],                      "knowledge_gap_archive",       "low",    True),

    # "fastest" contains substring "test" — must be before run_tests entry
    (["fastest money", "fastest revenue", "fastest path to money",
      "fastest money path"],                                       "business_opportunities",    "medium", False),

    # ── Standard commands ───────────────────────────────────────────────────────
    (["health", "backend", "system check", "check system"],      "health_check",              "medium", False),
    (["worker", "heartbeat", "workers"],                          "worker_status",             "medium", False),
    (["queue", "backlog", "pending signal"],                       "queue_status",              "medium", False),
    (["test", "run test"],                                         "run_tests",                 "medium", False),
    (["trading", "trade", "position", "oanda"],                    "trading_lab_status",        "high",   False),
    (["funding", "fund"],                                          "funding_status",            "medium", False),
    (["credit", "score", "fico"],                                  "credit_workflow_status",    "medium", False),
    (["grant", "grants"],                                          "grant_research_status",     "low",    False),
    (["research", "youtube", "signal"],                            "research_task",             "low",    False),
    # ── CEO digest / anomaly — must come before generic "ceo" keyword ────────
    (["ceo digest", "ceo report", "ceo brief", "executive digest",
      "daily digest", "show me the digest", "platform digest",
      "anomaly", "anomalies", "what's broken", "what is broken",
      "health report", "platform health"],                         "ceo_digest",                "high",   False),
    (["ceo", "daily report", "weekly report", "brief"],            "summarize_recent_activity", "high",   False),
    (["refactor", "fix", "build", "implement", "code", "write"],   "code_task",                 "high",   True),
    (["deploy", "push", "release", "rm ", "delete ", "drop "],     "code_task",                 "critical", True),
    (["summary", "summarize", "activity"],                         "summarize_recent_activity", "medium", False),

    # ── Nexus intelligence intents ───────────────────────────────────────────────
    (["business opportunity", "business opportunities", "what opportunities",
      "show opportunities", "best opportunity", "top opportunity",
      "side hustle", "ai content agency", "credit repair consulting",
      "funding broker", "opportunities ready",
      # monetization natural language phrases
      "how do we make money", "how can we make money",
      "how to make money today", "best money making opportunity",
      "what can make money", "money making opportunity",
      "best revenue move", "next best money move",
      "what should we monetize", "make money right now",
      # monetization audit and plan commands
      "nexus monetization audit", "run nexus monetization audit",
      "show monetization audit", "monetization audit",
      "monetization plan", "monetization priorities",
      "revenue plan for today", "fastest money path",
      "what is our fastest money path"],                            "business_opportunities",    "medium", False),
    (["app url", "website url", "what is the url", "what's the url",
      "app link", "platform url", "nexus url", "goclear",
      "what is the app", "where is the app", "how do i access"],   "app_url",                   "low",    False),
    (["onboarding", "getting started", "setup steps", "new user",
      "how to start", "first steps"],                              "onboarding_status",         "medium", False),
    (["user intelligence", "user score", "engagement score",
      "user profile", "user readiness", "who are my users"],       "user_intelligence_status",  "medium", False),
    (["platform analytics", "usage stats",
      "how many users", "user count", "active users"],             "platform_analytics",        "medium", False),
    # ── Source intake status queries ─────────────────────────────────────────
    (["show source intake", "what links did i send", "what youtube did i send",
      "what happened to the last link", "show failed source", "continue processing",
      "reroute this source", "assign this to claude", "assign to youtube",
      "show pending source", "source intake queue",
      "what artifacts did nexus create", "what did claude code finish",
      "what did codex finish", "show unregistered artifacts",
      "backfill the artifact registry"],                           "source_intake_status",       "medium", False),
    (["show artifact registry", "artifact registry", "show all artifacts",
      "what artifacts exist"],                                     "artifact_registry_status",   "low",    False),

    # ── Active operating rules (must be BEFORE memory sources and research catches) ──
    (["show active operating rules", "active operating rules",
      "what active rules are you using", "what rules are you following",
      "show hermes rules", "show live answer rules", "show approval rules",
      "what approval rules are active"],                               "active_operating_rules",     "low",    False),

    # ── Memory v2 preview commands (must be BEFORE memory sources) ──────────
    (["show memory v2 preview", "preview memory v2", "show hermes memory v2",
      "hermes memory v2", "memory v2 preview", "show v2 memory",
      "show v2 preview"],                                             "memory_v2_preview",          "low",    False),

    (["compare memory v2", "compare current memory and v2",
      "compare v2", "v2 vs current memory", "memory comparison",
      "compare memory readers", "v2 reader comparison"],             "memory_v2_compare",          "low",    False),

    (["show memory v2 rules", "memory v2 rules", "v2 operating rules",
      "what rules are in v2"],                                       "memory_v2_rules",            "low",    False),

    (["show memory v2 status", "memory v2 status", "v2 reader status",
      "is v2 reader active", "v2 status"],                          "memory_v2_status",           "low",    False),

    (["show memory v2 primary status", "memory v2 primary status",
      "is memory v2 primary active", "primary mode status",
      "v2 primary status"],                                         "memory_v2_primary_status",   "low",    False),

    (["show memory v2 shadow status", "memory v2 shadow status",
      "show shadow memory status", "shadow memory status",
      "v2 shadow status"],                                          "memory_v2_shadow_status",    "low",    False),

    (["is memory v2 live", "is memory v2 primary",
      "is memory v2 shadow only", "is v2 primary",
      "is v2 live", "is v2 the live reader",
      "has v2 switched", "did v2 switch"],                         "memory_v2_live_check",       "low",    False),

    # ── Memory sources / debug commands (must be BEFORE archived_executive_memory) ──
    # "again" variants force a fresh send even if content is identical to prior response
    (["show memory sources again", "memory sources again",
      "repeat memory sources", "resend memory sources"],             "memory_sources_again",       "low",    False),

    (["show memory sources", "memory sources", "what memory sources",
      "what are your memory sources", "where does your memory come from",
      "where do you get memory from", "what memory do you use",
      "what sources do you use", "show your memory sources"],         "memory_sources",             "low",    False),

    # ── Archived (stale) executive memory commands ──────────────────────────
    (["archived memory", "stale defaults", "load archived defaults",
      "show archived defaults", "archived executive memory",
      "what were the old defaults", "original defaults",
      "what was in the old executive memory",
      "show old executive memory", "show historical executive memory",
      "old executive memory", "historical executive memory"],        "archived_executive_memory", "low",    False),

    (["where did that answer come from", "where does that come from",
      "where does your answer come from", "cite that answer",
      "cite source", "answer source", "what source did you use",
      "why did you answer that"],                   "answer_source",               "low",    False),

    (["show stale memory debug", "stale memory debug", "stale debug",
      "debug memory", "show debug memory",
      "show blocked memory debug", "show deprecated memory debug",
      "blocked memory debug", "deprecated memory debug"],            "stale_memory_debug",        "low",    False),

    # ── Provider / brain status ──────────────────────────────────────────────
    (["what brain are you using", "which brain",
      "are you using chatgpt", "chatgpt auth", "are you using openai",
      "are you using openrouter", "is openrouter enabled", "openrouter status",
      "show provider status", "provider status", "which llm", "what llm",
      "what model are you using", "which model", "brain status",
      "disable openrouter", "disable open router",
      "show evidence mode status", "evidence mode status",
      "what provider", "which provider"],                          "provider_status",             "low",    False),

]


def classify_intent(text: str) -> tuple[str, Priority, bool]:
    import re as _re
    # Detect any URL → source intake
    if _re.search(r'https?://[^\s]+', text):
        return "source_intake", "medium", False
    lowered = text.lower()
    for keywords, intent, priority, requires_approval in _INTENT_MAP:
        if any(kw in lowered for kw in keywords):
            return intent, priority, requires_approval
    return "unknown", "medium", False
