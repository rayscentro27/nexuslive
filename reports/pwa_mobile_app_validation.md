# PWA / Mobile App Validation
**Date:** 2026-05-12  
**Scope:** App URL, PWA install, mobile behavior

---

## 1. The App

**Project:** nexuslive (~/nexuslive)  
**Repo:** https://github.com/rayscentro27/nexuslive.git  
**Netlify Site ID:** `739d0dbd-dd02-40b5-8607-b02b69708e02`  
**Framework:** Vite + React + TypeScript  
**Deploy:** Netlify (auto-deploy from GitHub)  
**Functions:** Netlify serverless (netlify/functions/)

---

## 2. Production URL — Status

The exact production URL cannot be determined from local files. Options:
1. Check Netlify dashboard at netlify.com/sites → find site with ID `739d0dbd-dd02-40b5-8607-b02b69708e02`
2. Run `netlify sites:list` (Netlify CLI needed)
3. The URL follows the pattern: `https://[site-name].netlify.app` or a custom domain if configured

**Why this matters:** The admin portal uses `window.location.origin` for invite links — if the URL is a preview URL or different from what users expect, invite links will point to the wrong place.

**Action required:** Determine the canonical production URL and add it as `VITE_APP_URL` in Netlify environment variables.

---

## 3. PWA Configuration

**Manifest:** `public/manifest.json`  
- `name`: "Nexus — Build Credit. Access Capital."  
- `short_name`: "Nexus"  
- `start_url`: `/`  
- App name is clear and professional

**Service Worker:** `dist/sw.js` exists ✅  
**Icons directory:** `dist/icons/` exists ✅  
**Build output:** `dist/` present — last build artifacts exist

---

## 4. PWA Install Flow (iPhone)

Standard iOS PWA install:
1. Open Safari → navigate to app URL
2. Tap Share button (box with arrow)
3. Tap "Add to Home Screen"
4. Confirm name → app installs

**Known iOS limitations:**
- Must use Safari — Chrome on iOS does NOT support PWA install
- PWA on iOS does NOT persist login across sessions by default (depends on storage implementation)
- Push notifications not supported on iOS PWA (as of iOS 16 — partially supported from iOS 17)

**Current install clarity issue:** If the landing page doesn't explicitly show "Add to Home Screen" instructions for iOS, users won't know how to install. Android Chrome shows an automatic install prompt; iOS never does.

---

## 5. Recommended Install Instructions (for Invites / Onboarding)

Add to the welcome email and/or the onboarding screen:

```
iPhone / iPad:
1. Open the link in Safari (not Chrome)
2. Tap the Share icon → "Add to Home Screen"
3. The Nexus app icon will appear on your home screen

Android:
1. Open the link in Chrome
2. Tap the three-dot menu → "Add to Home Screen" or "Install App"
```

---

## 6. Multi-URL Confusion Assessment

**Potential sources of confusion:**
- Netlify preview URLs (auto-generated on each PR/branch deploy)
- The main site URL
- Any custom domain if configured

**Recommended posture:**
- Set a single canonical URL as `VITE_APP_URL` in Netlify
- Use this in invite links, onboarding, and any documentation
- Disable preview URL sharing (or clearly label previews as non-production)

---

## 7. Validation Checklist (Manual — Requires Browser)

| Check | Method | Status |
|---|---|---|
| App loads at production URL | Open in browser | ❓ Not verified (need URL) |
| Login persists after close/reopen | Install + test | ❓ Not tested |
| Dashboard renders on iPhone | Mobile browser | ❓ Not tested |
| PWA install prompt appears (Android) | Android Chrome | ❓ Not tested |
| Add to Home Screen works (iPhone) | Safari share sheet | ❓ Not tested |
| App icon correct | After install | ❓ Not tested |
| Invite link → correct URL | Admin portal test | ❓ Needs VITE_APP_URL set |

---

## 8. Immediate Actions

1. **Determine canonical URL** — check Netlify dashboard for site `739d0dbd`
2. **Add `VITE_APP_URL`** to Netlify environment variables with the canonical URL
3. **Add `RESEND_API_KEY` + `RESEND_FROM_EMAIL`** (from invite email fix)
4. **Redeploy** to pick up all env var changes
5. **Test invite flow end-to-end** per invite_flow_validation.md test plan
6. **Add install instructions** to the onboarding screen and welcome email
