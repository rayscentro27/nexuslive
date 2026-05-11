# Business Task Executor

Consumes business `implementation_tasks` and turns them into concrete local
deliverables inside the generated site bundle.

Worker:

- `research_intelligence/business_task_executor.py`

Usage:

```bash
python3 -m research_intelligence.business_task_executor --limit 10
```

What it does:

1. Reads active business `implementation_projects` that already have a generated site bundle
2. Loads related `implementation_tasks`
3. Processes tasks for:
   - `OpportunityWorker`
   - `OpsAutomation`
   - `BackendEmployees`
4. Writes markdown deliverables into:
   - `generated_sites/<slug>/task_outputs/`
5. Marks those tasks `completed`
6. Marks the project `completed` if no active tasks remain

Typical outputs:

- offer packaging brief
- pricing/validation notes
- CRM workflow plan
- backend handoff notes
