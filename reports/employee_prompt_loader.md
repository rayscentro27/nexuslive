# Employee Prompt Loader

Date: 2026-05-15

Implemented dynamic employee prompt/profile loader in:
- `lib/ai_employee_prompt_loader.py`

Data sources:
- `ai_employees/prompts/*.md`
- `ai_employees/employee_profiles.json`

Exposed functions:
- `get_employee_prompt(employee_id)`
- `get_employee_voice(employee_id)`
- `get_employee_decision_framework(employee_id)`
- `get_employee_confidence_threshold(employee_id)`

Integrated with:
- `lib/ai_employee_registry.py`
