# NotebookLM Operator Workflow — Nexus Platform
Updated: 2026-05-12

## Overview

NotebookLM is your **research workspace** — not a permanent database.
Nexus Knowledge Brain (Supabase) is your **permanent memory**.
Hermes retrieves reviewed Nexus knowledge when you ask questions.

The flow is:
```
NotebookLM (research) → Export/Digest → Review Queue → Nexus Knowledge Brain → Hermes retrieves
```

---

## Architecture

| Layer | Tool | Purpose |
|-------|------|---------|
| Research | NotebookLM | Analyze PDFs, videos, articles; generate summaries |
| Export | NotebookLM CLI / Copy-Paste | Extract digests and key insights |
| Intake | Nexus Knowledge Queue | Dry-run queue for admin review |
| Permanent Store | Supabase Knowledge Brain | Approved, reviewed knowledge records |
| Retrieval | Hermes (internal-first) | Answers questions from Knowledge Brain |

---

## Step 1 — Create Your Notebooks

Create one notebook per knowledge domain. Never mix domains in one notebook — it makes prompting messy.

### Recommended Notebooks

#### 1. Trading Strategies Notebook
- **Sources to Add**: Trading transcripts, strategy PDFs, backtesting results, TradingView exports, YouTube trading videos
- **Name It**: `Nexus Trading Strategies 2026`
- **What to Ask NotebookLM**:
  - "Summarize all entry and exit rules across all sources"
  - "What are the key risk rules mentioned?"
  - "What timeframes perform best across all strategies?"
  - "Generate a strategy comparison table"
- **How to Export**: Copy the summary. Paste into `/knowledge/trading/` directory or submit via knowledge email
- **How Nexus Ingests**: Via knowledge email parser → admin review queue → approve → Supabase

#### 2. Business Funding Notebook
- **Sources to Add**: SBA PDFs, lender program guides, funding transcripts, funding research articles
- **Name It**: `Nexus Business Funding 2026`
- **What to Ask**:
  - "What are the fastest paths to $50K in funding for a new business?"
  - "What credit score is required for each program?"
  - "Compare SBA 7(a) vs EIDL vs MCA"
- **How to Export**: Digest email to goclearonline@gmail.com with subject "Knowledge Digest: Business Funding"
- **How Nexus Ingests**: Knowledge email parser routes to review queue

#### 3. Credit Repair Notebook
- **Sources to Add**: CFPB guides, dispute letter templates, credit repair training materials, FCRA PDFs
- **Name It**: `Nexus Credit Repair Playbook 2026`
- **What to Ask**:
  - "What are the 5 most effective dispute strategies?"
  - "What does the FCRA say about tradeline removal?"
  - "Generate a 90-day credit repair action plan"
- **How to Export**: Export key summaries to knowledge queue

#### 4. Grants Notebook
- **Sources to Add**: Grant program PDFs, SBIR guidelines, SBA resources, grant research articles
- **Name It**: `Nexus Grants Research 2026`
- **What to Ask**:
  - "Which programs have the highest approval rate for first-time applicants?"
  - "What are the common eligibility requirements across all sources?"
  - "What documents appear most often in grant applications?"
- **How to Export**: Monthly digest → knowledge email

#### 5. Business Opportunities Notebook
- **Sources to Add**: Business model articles, revenue reports, case studies, side hustle research
- **Name It**: `Nexus Business Opportunities 2026`
- **What to Ask**:
  - "Rank these opportunities by startup cost"
  - "Which opportunities require the least technical skill?"
  - "What are the first 3 steps for each business model?"

#### 6. Nexus Operations Notebook
- **Sources to Add**: Architecture docs, system summaries, AGENTS.md, implementation reports
- **Name It**: `Nexus Operations 2026`
- **What to Ask**:
  - "What are the known blockers?"
  - "What's the recommended next phase?"
  - "What services are running on the Oracle server?"

#### 7. Marketing Notebook
- **Sources to Add**: Competitor analyses, social media guides, content strategy docs, brand notes
- **Name It**: `Nexus Marketing 2026`
- **What to Ask**:
  - "What content formats work best for credit/funding audiences?"
  - "What CTAs convert best for financial services?"

---

## Step 2 — Research Session Workflow

1. Open NotebookLM and select the relevant notebook
2. Add sources (PDFs, YouTube links, web articles, pasted text)
3. Use the NotebookLM chat to extract insights
4. Use "Audio Overview" to generate a podcast-style summary (optional)
5. Copy key insights into a digest document

---

## Step 3 — Export/Bridge to Nexus

### Option A — Knowledge Email (Recommended)
Send an email to your knowledge intake address with:
- **Subject**: `Knowledge Digest: [Topic]`
- **Body**: Paste NotebookLM summary + key takeaways
- **What happens**: Nexus email parser captures → creates proposed Knowledge Brain record → pending admin review

### Option B — Direct Supabase Insert (Admin Only)
Use the Admin Knowledge Review UI to manually add a digest record.

### Option C — NotebookLM CLI Export (Advanced)
If the NotebookLM CLI is configured:
```bash
notebooklm export --notebook "Nexus Trading Strategies 2026" --format json | python3 nexus-ai/scripts/knowledge_intake.py
```

---

## Step 4 — Admin Review Queue

All imported knowledge goes to the **dry-run intake queue** first.
No knowledge enters Hermes until you approve it.

Steps:
1. Go to Admin Portal → Knowledge Reviews
2. Review proposed record
3. Approve → enters Knowledge Brain
4. Reject → discarded
5. Edit → modify before approving

**HERMES_KNOWLEDGE_AUTO_STORE_ENABLED=false** — no auto-store.

---

## Step 5 — Hermes Retrieves Approved Knowledge

Once approved, Hermes can answer:
- "What trading research is ready?"
- "What grant research is ready?"
- "Summarize the latest NotebookLM digest"
- "What knowledge items need review?"

---

## Important Rules

- NotebookLM is for YOUR research sessions — it is not a user-facing tool
- Never add sensitive client data to NotebookLM notebooks
- Always review before approving knowledge to Knowledge Brain
- NotebookLM notebook contents are not automatically synced to Nexus
- The operator (you) controls what enters the Knowledge Brain

---

## Quick Reference Commands

| What you want | Telegram command |
|---------------|-----------------|
| See pending knowledge | "What items need review?" |
| Check trading research | "What trading research is ready?" |
| Check grant research | "What grant research is ready?" |
| Trigger digest review | "Summarize latest NotebookLM digest" |
| See approved knowledge | "What knowledge is in the brain?" |
