# Nexus PWA User Onboarding Polish
**Date:** 2026-05-11  
**Status:** COMPLETE

---

## Problem

The post-deployment PWA email sent in the enablement pass was technically accurate but user-hostile. It contained:

- `curl` commands targeting `/manifest.json` and `/sw.js`
- "vite build" output (irrelevant to users)
- Internal file paths (`public/sw.js`, `src/main.tsx`)
- No user install instructions
- No app URL in a user-friendly format
- Developer tone, not operator/CEO tone

That content belongs in **internal technical reports only** — not in anything that goes to a user or a non-technical operator.

---

## Separation: Technical vs User-Facing

### Internal Technical Reports (developer audience)
**File:** `reports/pwa_enablement_summary.md`  
**Contains:** Build output, file paths, curl verification commands, service worker caching rules, netlify.toml notes  
**Audience:** Developers, AI system logs  
**Send to:** Internal only — do not forward to users

### User-Facing Onboarding Emails (user/operator audience)
**File:** `marketing/nexus_app_install_email.md`  
**Contains:** App URL, device-specific install steps, support guidance  
**Audience:** Beta users, operators, non-technical recipients  
**Send to:** rayscentro@yahoo.com for operator review; users on onboarding trigger

---

## User Install URL

```
https://gonexuslive.netlify.app
```

This is the only URL a user needs. All other links (manifest, sw.js, icons) are implementation details.

---

## Install Instructions by Device

### iPhone (Safari)
1. Open `https://gonexuslive.netlify.app` in **Safari** (not Chrome, not in-app browser)
2. Tap the **Share** button (square with upward arrow at bottom of screen)
3. Scroll down and tap **"Add to Home Screen"**
4. Tap **Add** in the top right

**Result:** Nexus icon appears on home screen, opens in standalone mode (no browser chrome)

**Common failure:** User opens in Chrome on iPhone — Chrome on iOS does not support Add to Home Screen installation from a PWA prompt. Must use Safari.

---

### Android (Chrome)
1. Open `https://gonexuslive.netlify.app` in **Chrome**
2. Either:
   - Tap the **install banner** that may appear at the bottom, OR
   - Tap the three-dot menu → **"Add to Home Screen"** or **"Install App"**
3. Tap **Install**

**Result:** Nexus icon in app drawer, opens without browser chrome  
**Note:** The `InstallPrompt` component in the app shows a bottom banner automatically when Chrome's `beforeinstallprompt` fires. User taps Install in the banner — no menu navigation needed.

---

### Desktop (Chrome or Edge)
1. Open `https://gonexuslive.netlify.app` in Chrome or Edge
2. Look for the **install icon** in the address bar (monitor with down arrow)
3. Click it → click **Install**

Alternatively: three-dot menu → **"Install Nexus"**

**Firefox:** Does not support PWA installation — inform user to switch to Chrome or Edge.  
**Safari on Mac:** Supported on macOS Ventura+ — File menu → "Add to Dock"

---

## PWA Technical Verification (Internal Only)

These checks confirm the PWA is deployed correctly. Not for user emails.

| Check | Command | Expected |
|-------|---------|---------|
| Manifest loads | `curl https://gonexuslive.netlify.app/manifest.json` | JSON with name, icons, display |
| Service worker reachable | `curl https://gonexuslive.netlify.app/sw.js` | JS file starting with `// Nexus PWA` |
| Icon 192 loads | `curl -I https://gonexuslive.netlify.app/icons/icon-192.png` | `200 OK` |
| Icon 512 loads | `curl -I https://gonexuslive.netlify.app/icons/icon-512.png` | `200 OK` |
| Apple touch icon | `curl -I https://gonexuslive.netlify.app/apple-touch-icon.png` | `200 OK` |

**Status:** Pending live Netlify deploy. All artifacts are committed and will be served after next deploy from `agent-coord-clean`.

---

## Install Banner Behavior

The `InstallPrompt` component in `src/components/InstallPrompt.tsx`:

- Fires only when Chrome/Edge triggers `beforeinstallprompt` (Android + Desktop Chrome/Edge)
- Does NOT appear on iPhone (iOS shows "Add to Home Screen" via Safari share sheet only)
- Session-dismissed: once user closes it, it won't reappear in same session
- No persistent suppression across sessions (intentional — user may want to install later)
- Positioned at bottom of screen, never blocks content

---

## Devices to Test After Deploy

| Device | Browser | Install Method | Expected |
|--------|---------|----------------|---------|
| iPhone 14+ | Safari | Share → Add to Home Screen | Standalone mode, navy icon |
| iPhone (older) | Safari | Share → Add to Home Screen | Same |
| Android (Pixel/Samsung) | Chrome | Banner prompt or menu | Standalone mode |
| Mac Desktop | Chrome | Address bar icon | Standalone window |
| Mac Desktop | Edge | Address bar icon | Standalone window |
| Mac Desktop | Safari (Ventura+) | File → Add to Dock | Dock icon |
| Windows Desktop | Chrome | Address bar icon | Standalone window |

---

## Remaining Blockers

| Blocker | Status | Resolution |
|---------|--------|-----------|
| Netlify deploy | Pending | Push `agent-coord-clean` branch; auto-deploys on Netlify |
| Live URL verification | Pending | Run curl checks after deploy |
| Real device test (iPhone) | Pending | Manual test by operator |
| Real device test (Android) | Pending | Manual test by operator |
| App icon visual check | Pending | Confirm navy + indigo "N" renders on home screen |
| Theme-color on iOS status bar | Pending | Verify #0F172A shows correctly |

---

## Email Separation Policy (Going Forward)

| Report Type | Contains | Sent To |
|-------------|---------|---------|
| Internal deployment report | Build output, file paths, curl commands, SW rules | Operator/developer logs only |
| User onboarding email | App URL, install steps, support info | Users, beta invitees |
| Telegram notification | One-line status only | Operator Telegram |

**Rule:** Any email that could go to a user must pass this check: "Would a non-technical person find this confusing?" If yes, it belongs in the internal report, not the user email.
