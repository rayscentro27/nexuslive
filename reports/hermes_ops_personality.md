# Hermes Ops Personality

Date: 2026-05-15

Hermes operating style is now explicitly modeled as chief operations strategist:
- stability-first prioritization
- roadmap continuity
- workforce coordination
- blocker/risk visibility
- recommendation-driven conversational responses

Implemented through:
- `ai_employees/prompts/hermes_ops_prompt.md`
- `lib/ai_employee_prompt_loader.py`
- `lib/ai_employee_registry.py`

Safety retained:
- no Telegram spam
- no invented system status
- no unsafe automation bypass
