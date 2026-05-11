# Nexus Research Source Pack — Status

**File:** `workflows/autonomous_research_supernode/sample_sources.json`
**Last updated:** 2026-03-12
**JSON valid:** ✅

---

## Source Counts

| Metric | Count |
|---|---|
| Total sources | 33 |
| Websites (browser lane) | 22 |
| YouTube channels (transcript lane) | 11 |

---

## Breakdown by Topic

| Topic | Total | Websites | YouTube |
|---|---|---|---|
| `credit_repair` | 10 | 6 | 4 |
| `grant_research` | 8 | 8 | 0 |
| `business_opportunities` | 6 | 3 | 3 |
| `trading` | 6 | 2 | 4 |
| `crm_automation` | 3 | 3 | 0 |

---

## Website Sources (Browser Lane)

### credit_repair
- CFPB Credit Report Disputes — consumerfinance.gov
- USA.gov Credit Report Errors — usa.gov
- Experian Dispute Center — experian.com
- TransUnion Credit Disputes — transunion.com
- Equifax Credit Report Help — equifax.com
- Help Me Build Credit - 0% APR Business Credit Cards — helpmebuildcredit.com

### grant_research
- Grants.gov — grants.gov
- Grants.gov Eligibility — grants.gov/learn-grants
- SBA Funding Programs — sba.gov/funding-programs
- SBA Grants — sba.gov/funding-programs/grants
- Hello Alice Grants — helloalice.com
- SCORE — score.org
- Arizona Commerce Authority — azcommerce.com
- SBIR.gov — sbir.gov

### business_opportunities
- Starter Story — starterstory.com
- Indie Hackers — indiehackers.com
- MicroAcquire / Acquire — acquire.com

### crm_automation
- HubSpot Blog - CRM — blog.hubspot.com/sales
- Zapier Blog Automation — zapier.com/blog
- Make Blog — make.com/en/blog

### trading
- OANDA Learn — oanda.com/us-en/trade-tap-blog
- CBOE Education — cboe.com/optionsinstitute

---

## YouTube Channel Sources (Transcript Lane)

### credit_repair
- Credit Plug — @creditplug
- Monica Main — @MonicaMain
- Darius Benders — @Dariusbenders
- Fix Your Credit Faster — @fixyourcreditfaster

### business_opportunities
- Alex Hormozi — @AlexHormozi
- Codie Sanchez — @CodieSanchezCT
- Tech Conversations — @TechConversations

### trading
- Option Alpha — /c/OptionAlpha
- SMB Capital — @SMBCapital
- Options With Ravish — @OptionsWithRavish
- Luuk Alleman — @LuukAlleman

---

## Recommended First-Run Order

Run each block in a separate terminal session. Use `--browser` first (faster, no yt-dlp needed),
then `--transcript` for YouTube (requires yt-dlp, slower).

### Block 1 — credit_repair (highest priority)
```bash
cd ~/nexus-ai/workflows/autonomous_research_supernode

# Websites only — fast, no yt-dlp needed
node research_orchestrator.js --once --browser --topic credit_repair

# YouTube channels — requires yt-dlp
node research_orchestrator.js --once --transcript --topic credit_repair
```

### Block 2 — grant_research (8 websites, no YouTube)
```bash
node research_orchestrator.js --once --browser --topic grant_research
```

### Block 3 — business_opportunities
```bash
node research_orchestrator.js --once --browser --topic business_opportunities
node research_orchestrator.js --once --transcript --topic business_opportunities
```

### Block 4 — trading
```bash
node research_orchestrator.js --once --browser --topic trading
node research_orchestrator.js --once --transcript --topic trading
```

### Block 5 — crm_automation (3 websites, no YouTube)
```bash
node research_orchestrator.js --once --browser --topic crm_automation
```

---

## Safe Validation Commands (run these first)

```bash
cd ~/nexus-ai/workflows/autonomous_research_supernode

# 1. Validate JSON
node -e "JSON.parse(require('fs').readFileSync('sample_sources.json','utf8')); console.log('JSON valid')"

# 2. Check source counts
node -e "
import('./source_registry.js').then(({ loadSources, filterByLane, filterByTopic, LANE }) => {
  const all = loadSources('sample_sources.json');
  const byTopic = all.reduce((a,s)=>{ a[s.topic]=(a[s.topic]||0)+1; return a; }, {});
  console.log('Total:', all.length, '| By topic:', JSON.stringify(byTopic));
});"

# 3. Single-source smoke test (browser, credit_repair, 1 source)
node research_orchestrator.js --once --browser --topic credit_repair --limit 1

# 4. Single-source smoke test (browser, grant_research, 1 source)
node research_orchestrator.js --once --browser --topic grant_research --limit 1
```

---

## Prerequisites

- `yt-dlp` — required for transcript lane: `brew install yt-dlp` or `pip install yt-dlp`
- `.env` — symlinked at `workflows/autonomous_research_supernode/.env → ../../.env`
- Required `.env` keys: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- Optional: `OPENCLAW_AUTH_TOKEN` (AI extraction), `HF_TOKEN` (vector embeddings)

---

## System Files Verified ✅

All 15 required orchestrator files present:

| File | Status |
|---|---|
| research_orchestrator.js | ✅ |
| source_registry.js | ✅ |
| transcript_extractor.js | ✅ |
| manual_source_loader.js | ✅ |
| topic_classifier.js | ✅ |
| claim_extractor.js | ✅ |
| artifact_writer.js | ✅ |
| memory_enricher.js | ✅ |
| graph_enricher.js | ✅ |
| cluster_writer.js | ✅ |
| brief_generator.js | ✅ |
| next_action_generator.js | ✅ |
| comet_researcher.js | ✅ |
| telegram_research_alert.js | ✅ |
| telegram_brief_alert.js | ✅ |
