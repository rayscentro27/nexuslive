# Hermes Internal-First Response Engine

Date: 2026-05-10

## Goal
Route Telegram conversational answers through internal Nexus/Hermes records first, then fall back to general model responses only when no internal match exists.

## Implementation
- Added `lib/hermes_internal_first.py`.
- Added internal-first hook in `telegram_bot.py` conversational path.
- Added confidence/source signaling in short chat responses:
  - `INTERNAL_CONFIRMED`
  - `INTERNAL_PARTIAL`
  - `GENERAL_FALLBACK` (used when no internal match)

## Internal Sources Used
- Operational memory (`lib/hermes_ops_memory`)
- Funding and recommendation retrieval (`lib/hermes_knowledge_brain`)
- Knowledge intake recency (`lib/hermes_email_knowledge_intake`)
- Demo/remote readiness (`lib/demo_readiness`)

## Config Pattern
- Safe runtime config via env key:
  - `HERMES_INTERNAL_FIRST_KEYWORDS` (JSON map)
- This is the non-destructive equivalent of a runtime config table for now.

## Behavior Notes
- Internal-first activates only on explicit operational phrases; normal chat remains conversational.
- Reply format stays Telegram-short and action-oriented.
- No changes to automation safety flags.

## Validation
- Added `scripts/test_hermes_internal_first.py`.
- Full Telegram pipeline tests passed after integration.

## Completion
- Telegram completion sent: `✅ Hermes internal-first intelligence enabled.`
