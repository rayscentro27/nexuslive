# Next Steps Intelligence Engine

Date: 2026-05-15

Implemented conversational next-step intelligence in `lib/hermes_roadmap_intelligence.py`.

Inputs used for recommendations:
- dynamic roadmap task state
- task priority scores and blockers
- worker recommendation per task
- latest lessons

System outputs:
- top priorities
- next 20 steps
- weak/blocked system areas
- tester readiness view
- worker-targeted recommendations (OpenCode/Claude Code)

Hermes command integration is handled in `lib/hermes_supabase_first.py` with conversational responses and reasoning-oriented guidance.
