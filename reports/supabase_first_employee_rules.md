# Supabase-First Employee Rules

Date: 2026-05-15

Applied and reinforced across employee stack:
1. Supabase-first retrieval
2. Prefer approved knowledge
3. Treat proposed/researching with caution
4. Escalate via research ticket when confidence is low
5. No invented facts
6. Explain uncertainty explicitly
7. Recommend next action
8. Persist lessons in roadmap continuity layer
9. Feed useful outcomes into knowledge workflow via existing ticket/review process
10. Preserve domain-specific tone per employee

Code changes:
- `lib/ai_employee_knowledge_router.py` (role-specific thresholds, unsafe-promise guard)
- `lib/ai_employee_registry.py` (profile-aware thresholds/framework)
