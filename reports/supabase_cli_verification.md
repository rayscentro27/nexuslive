# Supabase CLI Verification

Date: 2026-05-13
Workspace: `/Users/raymonddavis/nexus-ai`
Mode: Read-only verification

## Link verification

- Supabase CLI version: `2.90.0`
- Linked project ref: `ygqglfbhxiumqdisauar`
- Linked project metadata detected in `supabase/.temp/linked-project.json`
- Note: `supabase status` failed because local Docker daemon is not running; remote verification proceeded via Supabase REST endpoints using configured service credentials.

## Table checks

### knowledge_items

- Approved count: `10`
- Proposed count: `4`
- Latest 10 (`title`, `status`, `quality_score`, `domain`, `approved_at`, `created_at`):
  1. [Proposed] What opportunities are Nexus validated? | proposed | 40 | business | null | 2026-05-13T19:59:32.912629+00:00
  2. [Proposed] What trading research is available internally? | proposed | 40 | trading | null | 2026-05-13T19:59:30.606474+00:00
  3. [Proposed] What new knowledge was recently approved? | proposed | 40 | platform | null | 2026-05-13T19:59:28.800092+00:00
  4. [Proposed] What grant opportunities has Nexus researched? | proposed | 40 | grants | null | 2026-05-13T19:59:27.185346+00:00
  5. Can Nexus find grants for AI education businesses? | approved | 85 | grants | 2026-05-13T20:07:04.320823+00:00 | 2026-05-13T19:59:25.392582+00:00
  6. What funding paths has Nexus researched for startups? | approved | 85 | funding | 2026-05-13T20:07:04.320823+00:00 | 2026-05-13T19:59:23.550548+00:00
  7. Can Nexus review AI automation affiliate opportunities? | approved | 85 | business | 2026-05-13T20:07:04.320823+00:00 | 2026-05-13T19:59:21.071328+00:00
  8. What does Nexus know about the ICT silver bullet strategy? | approved | 85 | trading | 2026-05-13T20:07:04.320823+00:00 | 2026-05-13T19:59:14.360227+00:00
  9. Can Nexus research the ICT silver bullet strategy? | approved | 85 | trading | 2026-05-13T20:07:04.320823+00:00 | 2026-05-13T19:59:12.616621+00:00
  10. [Proposed] hello alice small business grant | approved | 40 | grants | null | 2026-05-13T18:32:44.042373+00:00

### research_requests

- Count by status:
  - `needs_review`: `14`
- Latest 10 (`topic`, `department`, `status`, `priority`, `created_at`, `updated_at`) captured successfully.

### transcript_queue

- Total count: `0`
- Latest 10: none
- NitroTrades/youtube target checks:
  - `NitroTrades`: none
  - `youtube`: none
  - `https://www.youtube.com/@nitrotrades`: none

### user_opportunities

- Total count: `3`
- Rows (`opportunity_name`, `risk_level`, `opportunity_score`, `nexus_status`, `created_at`):
  - CDFI Microloan | low | 43 | validated | 2026-05-13T17:31:01.574934+00:00
  - Dedicated Business Checking Account | low | 63 | validated | 2026-05-13T17:31:01.288608+00:00
  - Hello Alice Small Business Grant | low | 63 | validated | 2026-05-13T17:31:00.921322+00:00

### provider_health

- Latest provider statuses:
  - ollama: offline
  - groq: online
  - openrouter: online
  - claude_cli: offline
  - codex: offline
  - opencode: offline
  - notebooklm: online

### analytics_events

- Today event count: `0`
- Latest event types: none
