# Nexus Social Account Inventory
**Last Updated:** 2026-05-11  
**Owner:** Raymond Davis / GoClearOnline  
**Status:** Pre-launch — manual setup in progress

---

## Account Registry

| Platform | Account/Page Name | URL | Owner/Admin | 2FA Enabled | Connected To | API Access | Posting Status | Notes |
|----------|------------------|-----|-------------|-------------|--------------|------------|---------------|-------|
| YouTube | Fund Your Business | TBD | Raymond Davis | — | Google Account | Not requested | Manual only | Channel to be created; primary long-form + Shorts platform |
| Instagram | @gonexuslive or @fundyourbusiness | TBD | Raymond Davis | — | Meta Business Suite | Not requested | Manual only | Business account; connect to Facebook Page |
| Facebook | Nexus / GoClearOnline Page | TBD | Raymond Davis | — | Meta Business Suite | Not requested | Manual only | Facebook Page; linked to Instagram |
| TikTok | @gonexuslive or @fundyourbusiness | TBD | Raymond Davis | — | TikTok Business Center | Not requested | Manual only | Short-form video; repurpose Reels/Shorts |
| LinkedIn | Raymond Davis / Nexus Company Page | TBD | Raymond Davis | — | LinkedIn | Not requested | Manual only | Authority posts; B2B reach |
| X/Twitter | @gonexuslive or @nexusplatform | TBD | Raymond Davis | — | X/Twitter | Not requested | Manual only | Build-in-public; thought leadership |

---

## Field Definitions

| Field | Description |
|-------|-------------|
| 2FA Enabled | Whether two-factor authentication is active on the account |
| Connected To | Platform dashboard the account is managed through |
| API Access | Whether a developer app/API key has been created (none yet) |
| Posting Status | `Manual only` = no auto-posting; `Scheduled manually` = tool-assisted but human-approved |

---

## Setup Priority Order

1. YouTube — Fund Your Business channel (primary content engine)
2. Instagram Business account (highest organic reach for funding niche)
3. Facebook Page (required for Meta Business Suite)
4. TikTok (repurpose Reels/Shorts)
5. LinkedIn (authority and B2B)
6. X/Twitter (build-in-public)

---

## Security Policy

- All accounts protected with 2FA before any content is published
- No API tokens stored in plaintext — use environment variables if/when API access is requested
- No third-party auto-posting tools until manually reviewed and approved
- No social credentials in code repositories
- API access will require explicit approval before activation
- All accounts owned by Raymond Davis; no shared credentials

---

## Status Key

| Status | Meaning |
|--------|---------|
| Not created | Account does not yet exist |
| Created | Account exists, not yet configured |
| Configured | Profile complete, 2FA enabled |
| Active | Publishing content manually |
| API-connected | Developer app created (requires approval) |
