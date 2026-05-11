# Research Approval Handoff

Once an operator approves a row in `research_recommendations`, the handoff worker
can create implementation-ready records for backend employees.

New tables:

- `implementation_projects`
- `implementation_tasks`

Worker:

- `research_intelligence/approval_handoff_worker.py`

Usage:

```bash
python3 -m research_intelligence.approval_handoff_worker --once
```

What it does:

1. Reads `research_recommendations` where:
   - `approval_status = 'approved'`
   - `metadata.handoff_created != true`
2. Creates one `implementation_projects` row
3. Expands `execution_plan` + `backend_handoff` into `implementation_tasks`
4. Writes a `workflow_outputs` summary for dashboards
5. Marks the recommendation as:
   - `approval_status = 'executing'`
   - `metadata.handoff_created = true`

Business recommendation example:

- WebsiteBuilder: create sitemap and landing page structure
- OpsAutomation: set up CRM capture and analytics
- OpportunityWorker: define offer/pricing/launch checklist

Trading recommendation example:

- TradingEngine: attach risk + replay evidence
- ResearchDesk: verify calibration and execution notes
- TradingEngine: prepare paper-trader promotion payload

This is the bridge between:

- research insight
- operator approval
- backend employee execution
