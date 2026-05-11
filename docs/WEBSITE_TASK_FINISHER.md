# Website Task Finisher

Consumes ready `WebsiteBuilder` implementation tasks and writes concrete page
assets into the generated site bundle.

Worker:

- `research_intelligence/website_task_finisher.py`

Usage:

```bash
python3 -m research_intelligence.website_task_finisher --limit 10
```

What it does:

1. Reads active business projects with a generated site bundle
2. Finds `WebsiteBuilder` tasks in `ready`, `pending`, or `in_progress`
3. Writes concrete assets such as:
   - `landing-page-copy.md`
   - `sitemap-outline.md`
   - `service-pages.html`
4. Marks those tasks `completed`
5. Marks the project `completed` if no active tasks remain
