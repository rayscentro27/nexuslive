# Hermes Email Knowledge Intake (Dry-Run)

- timestamp: 2026-05-10T21:51:27.109673+00:00
- sender: ray@example.com
- subject: Knowledge Load - Funding Research
- message_id: msg-dup
- category_detected: funding
- priority: high
- tags: funding, credit

## Links Found
- https://example.com/business-funding-guide
- https://youtube.com/watch?v=abcd1234

## Duplicate Detection
- duplicates: 3
- new_proposed_records: 0

## Proposed Knowledge Brain Records
- proposed_total: 3
- mode: dry-run (no Supabase write)

## Next Steps
- Review proposed records in queue file.
- Approve records before any storage path is enabled.
- Keep HERMES_KNOWLEDGE_AUTO_STORE_ENABLED=false until manual sign-off.