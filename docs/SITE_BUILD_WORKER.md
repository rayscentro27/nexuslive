# Site Build Worker

`research_intelligence/site_build_worker.py` consumes queued business
implementation projects and scaffolds a local site bundle in:

`generated_sites/<slug>/`

Generated files:

- `index.html`
- `styles.css`
- `site-plan.json`
- `README.md`

It reads:

- `implementation_projects`
- `implementation_tasks`
- `research_recommendations`

It updates:

- `implementation_projects.status -> in_progress`
- `implementation_projects.metadata.site_bundle_path`
- website-oriented tasks to `status = ready`

Run:

```bash
python3 -m research_intelligence.site_build_worker --limit 5
```

This is the first automated backend-employee step after approval:

1. Operator approves recommendation
2. `approval_handoff_worker` creates implementation project + tasks
3. `site_build_worker` creates the initial site bundle
4. Website/content workers iterate from the generated scaffold
