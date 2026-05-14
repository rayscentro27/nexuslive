# Live Telegram Spam Forensics

Generated: 2026-05-14

## Observed Spam Signature
- "NEXUS OPPORTUNITY BRIEF"
- "X opportunities detected"
- "Grant Programs Overview" / grant opportunity cards

## Exact Source Trace
- Opportunity spam chain:
  - Worker: `workflows/ai_workforce/opportunity_worker/opportunity_worker.js`
  - Function: `sendOpportunityBriefAlert(...)`
  - Sender: `workflows/ai_workforce/opportunity_worker/opportunity_brief_generator.js`
  - Telegram text template contains exact phrase `NEXUS OPPORTUNITY BRIEF`.
- Grant spam chain:
  - Worker: `workflows/ai_workforce/grant_worker/grant_worker.js`
  - Function: `sendGrantBriefAlert(...)`
  - Sender: `workflows/ai_workforce/grant_worker/grant_brief_generator.js`

## Launch/Trigger Attribution
- LaunchAgent files existed for both opportunity + grant workers (`~/Library/LaunchAgents/com.nexus.opportunity-worker.plist`, `com.nexus.grant-worker.plist`).
- These LaunchAgents were removed in this pass.

## Policy Bypass Determination
- Both brief generators previously called Telegram API directly without central policy check.
- This was a true bypass path and capable of producing autonomous summary spam.

## Overlap / Duplicate Risk
- Duplicate risk existed via launchd workers + cron jobs + additional workflow summary senders.
- Active overlap reduced by removing launchd workers and denying brief event types.
