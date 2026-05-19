# Nexus Opportunity Engine

**Created:** 2026-05-18  
**Status:** 3 subtasks queued — research_worker assigned  
**Purpose:** Structured research board for real business opportunities

---

## Scoring Framework

Each opportunity is scored 1–10 on five dimensions:

| Dimension | Description |
|-----------|-------------|
| **Startup Cost** | 10 = $0, 1 = $10K+ |
| **Speed to Revenue** | 10 = <1 week, 1 = >6 months |
| **Scalability** | 10 = unlimited scale, 1 = hard ceiling |
| **Nexus Fit** | 10 = Nexus does most of the work |
| **Automation Potential** | 10 = fully automated, 1 = all manual |

**Composite score = weighted average (×2 on Nexus Fit and Automation)**

---

## Opportunity Board Categories

| Stage | Description |
|-------|-------------|
| **Researching** | Gathering data, scoring, evaluating |
| **Testing** | Running minimum viable experiment |
| **Monetizing** | Actively generating revenue |
| **Scaling** | Growing systematically |
| **Failed** | Tried, documented lessons, moving on |

---

## Initial Opportunity List

### Tier 1 — High Score Opportunities (Score 40+)

**1. Affiliate Marketing — Business/Funding Niche**
- Startup: $0 | Speed: 1 week | Scale: high | Nexus: high | Auto: high
- Programs: Bluevine, Novo, Nav, Lendio, Fundera
- Action: Research subtask queued

**2. Faceless YouTube — Business Credit / Funding Education**
- Startup: $0 | Speed: 2 weeks | Scale: very high | Nexus: high | Auto: medium
- Monetize: AdSense + affiliates + offers
- Action: Script generation ready

**3. Grant Research Service**
- Startup: $0 | Speed: 1 week | Scale: medium | Nexus: very high | Auto: very high
- `grant_research_v1` skill already built
- Action: Pricing + landing page needed

**4. Lead Generation for B2B / Local Business**
- Startup: $0 | Speed: 2 weeks | Scale: high | Nexus: high | Auto: high
- Sell leads to business service providers (lawyers, accountants, lenders)
- Action: Define niche + scraping approach

**5. AI-Generated Content Agency (B2B)**
- Startup: $50 (AI tools) | Speed: 1–2 weeks | Scale: very high
- Nexus drafts, Ray sells, deliver AI-written articles/SEO/social
- Action: Productize offer, set pricing

---

### Tier 2 — Medium Score Opportunities (Score 25–40)

**6. App Idea: Business Credit Tracker**
- Simple web app showing business credit score progress
- Monetize: $19/month subscription
- Nexus can build MVP on nexuslive platform
- Startup: $0 | Speed: 4 weeks | Scale: very high

**7. SEO Content Farm (Programmatic SEO)**
- Target: long-tail business funding / credit keywords
- Nexus generates articles, WordPress publishes
- Monetize: AdSense + affiliate links
- Startup: $15/mo hosting | Speed: 4 weeks | Scale: very high

**8. Drop Servicing — AI Marketing Agency**
- Sell AI marketing services, fulfill with Nexus tools
- Startup: $0 | Speed: 2 weeks | Scale: medium

**9. Business Credit Consulting (Productized)**
- $197 report + $97/month monitoring
- Nexus automates report generation
- Risk: medium (credit-related disclaimers required)

**10. Automation Service for Small Businesses**
- Build Zapier/Make automations for local businesses
- $500–2,000 per client setup + $97/month maintenance
- Nexus generates automation plans and documentation

---

### Tier 3 — Research Pending

**11. Forex/Crypto Signal Newsletter (Paper → Real, 6+ months)**
- NO live trading until 6+ months of verified paper performance
- Monthly newsletter format only
- Risk gate: requires multiple approval levels

**12. Mobile Home / Real Estate Research Tool**
- From research-engine content (JT Automations strategy)
- Simple deal analysis tool

**13. Dollar General Arbitrage Tracker**
- From research-engine content (JT Automations strategy)
- App for retail arbitrage deal finding

---

## Research Subtasks in Supabase

| # | Title | Agent | Status |
|---|-------|-------|--------|
| 06 | Research low-cost online business models (top 10, ranked) | research_worker | queued |
| 07 | Score each opportunity: startup cost, speed, scalability, Nexus fit, automation | hermes_orchestrator | queued |
| 08 | Create Opportunity Board categories | hermes_orchestrator | queued |

---

## Quick Win Experiments (Start This Week)

```bash
# Kick off affiliate research
python3 bin/nexus dispatch "research top 5 affiliate programs for business funding niche, include commission rates and approval requirements"

# Start faceless YouTube research
python3 bin/nexus dispatch "research top 5 faceless YouTube niches in business/credit/funding space, score by competition, monetization potential, and content production difficulty"

# SEO opportunity research
python3 bin/nexus dispatch "research programmatic SEO opportunities in business credit and funding niche, identify 20 low-competition keywords with search volume"
```

---

## Failure Conditions

Document here when opportunities are moved to **Failed**:
- (empty — none failed yet)
