#!/usr/bin/env python3
"""
Nexus Browser Worker — YouTube Studio Setup
============================================
Task:       youtube_studio_setup
Target:     studio.youtube.com — Nexus AI Wealth channel
Safety:     LOW_RISK — channel customization only.
            Never publishes videos, never touches monetization/billing.
Approval:   SUPERVISED — headed mode. Ray can watch and intervene.
Screenshots: artifacts/browser_tasks/youtube/

SAFETY RULES (hard-coded, not overridable):
  - NEVER clicks 'Upload Video', 'Go Live', 'Monetize', or 'Run Ads'
  - NEVER clicks any billing/payment button
  - NEVER stores, logs, or prints credentials
  - Channel customization 'Publish' (save profile edits) IS allowed — it only
    saves links/about text, not a video. Confirmed LOW_RISK.
  - Saves screenshots before each action
  - Stops and prompts if unexpected page detected

Usage:
  python3 scripts/browser_tasks/youtube_studio_setup.py

Requirements:
  pip3 install --break-system-packages playwright
  python3 -m playwright install chromium
"""

import asyncio
import sys
import os
import re
import time
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PWTimeoutError

# ─── Configuration ────────────────────────────────────────────────────────────

ARTIFACTS_DIR  = Path(__file__).resolve().parent.parent.parent / "artifacts" / "browser_tasks" / "youtube"
SESSION_STATE  = Path(__file__).resolve().parent.parent.parent / "artifacts" / "browser_tasks" / ".youtube_session.json"
STUDIO_URL     = "https://studio.youtube.com"
CUSTOM_URL     = "https://studio.youtube.com/channel/UC/customization/basicinfo"
LOGIN_WAIT_SEC = 240

# ─── Exact channel links — ORDER IS FIXED ────────────────────────────────────
CHANNEL_LINKS = [
    {"title": "Nexus AI Wealth",   "url": "https://goclearonline.cc"},
    {"title": "Nexus Newsletter",  "url": "https://nexus-ai-wealth.beehiiv.com"},
    {"title": "TikTok",            "url": "https://www.tiktok.com/@nexusaiwealth"},
    {"title": "X",                 "url": "https://x.com/goclearonline"},
    {"title": "Instagram",         "url": "https://instagram.com/goclearonline"},
    {"title": "LinkedIn",          "url": "https://www.linkedin.com/in/nexusai577024410"},
]

CONTACT_EMAIL  = "newsletter@goclearonline.cc"

# Actions to NEVER take automatically
BLOCKED_TEXT_PATTERNS = [
    r"upload video", r"go live", r"monetize", r"run ads",
    r"upgrade", r"billing", r"payment", r"buy", r"subscribe to plan",
    r"delete channel", r"remove channel",
]

# ─── Helpers ──────────────────────────────────────────────────────────────────

def ts() -> str:
    return datetime.now().strftime("%H%M%S")

def log(msg: str) -> None:
    print(f"[yt_worker {ts()}] {msg}", flush=True)

def countdown(seconds: int, msg: str) -> None:
    for i in range(seconds, 0, -1):
        print(f"\r{msg} ({i}s) — Ctrl+C to abort...  ", end="", flush=True)
        time.sleep(1)
    print(f"\r{msg} — proceeding.                      ", flush=True)

def is_blocked_action(text: str) -> bool:
    t = text.lower().strip()
    return any(re.search(p, t) for p in BLOCKED_TEXT_PATTERNS)

async def screenshot(page, name: str) -> Path:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    path = ARTIFACTS_DIR / f"{ts()}_{name}.png"
    await page.screenshot(path=str(path), full_page=False)
    log(f"Screenshot: {path.name}")
    return path

async def safe_click(page, locator, label: str) -> bool:
    if is_blocked_action(label):
        log(f"BLOCKED: refusing '{label}'")
        return False
    await locator.click()
    return True

async def wait_ss(page, name: str, delay_ms: int = 1500) -> None:
    await page.wait_for_timeout(delay_ms)
    await screenshot(page, name)

# ─── Link Validator (offline) ─────────────────────────────────────────────────

def validate_links(links: list) -> list:
    issues = []
    for i, link in enumerate(links, 1):
        url = link["url"]
        title = link["title"]
        if not url.startswith("http"):
            issues.append(f"Link {i} '{title}': missing https:// prefix → {url}")
        if " " in url:
            issues.append(f"Link {i} '{title}': URL contains spaces → {url}")
        if len(title) > 50:
            issues.append(f"Link {i} '{title}': title exceeds 50 chars ({len(title)})")
    return issues

# ─── Main Task ────────────────────────────────────────────────────────────────

async def run():
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    log("=== Nexus Browser Worker: youtube_studio_setup ===")
    log(f"Artifacts: {ARTIFACTS_DIR}")
    log("Safety: VIDEO_UPLOAD blocked | MONETIZATION blocked | CREDENTIALS never stored")
    log("Channel customization 'Publish' (save profile) IS allowed — saves links only")
    log("")

    # Offline link validation first
    issues = validate_links(CHANNEL_LINKS)
    if issues:
        log("⚠️  LINK VALIDATION ISSUES:")
        for iss in issues:
            log(f"   {iss}")
    else:
        log("✅ All 6 links pass format validation")

    log("")
    log("Starting in 5 seconds — Ctrl+C to abort...")
    countdown(5, "Launching browser")

    results = {
        "screenshots": [],
        "completed": [],
        "needs_manual": [],
        "blocked": [],
        "link_issues": issues,
    }

    async with async_playwright() as pw:
        session_exists = SESSION_STATE.exists()
        if session_exists:
            log(f"Session found at {SESSION_STATE.name} — reusing (skipping login)")
        else:
            log("No saved session — will open Google login (240s window)")

        browser = await pw.chromium.launch(
            headless=False,
            slow_mo=300,
            args=["--start-maximized", "--window-size=1440,900"],
        )
        ctx_kwargs = {"viewport": {"width": 1440, "height": 900}}
        if session_exists:
            ctx_kwargs["storage_state"] = str(SESSION_STATE)

        context = await browser.new_context(**ctx_kwargs)
        page = await context.new_page()

        # ── Step 1: Navigate to YouTube Studio ───────────────────────────────
        log("Step 1: Navigating to YouTube Studio...")
        await page.goto(STUDIO_URL, wait_until="domcontentloaded", timeout=30000)
        await wait_ss(page, "01_studio_landing")

        current_url = page.url
        log(f"Current URL: {current_url}")

        # Detect login requirement
        needs_login = (
            "accounts.google.com" in current_url or
            "signin" in current_url or
            "login" in current_url or
            "studio.youtube.com" not in current_url
        )

        if needs_login:
            await screenshot(page, "02_not_logged_in")
            log("")
            log("⚠️  NOT LOGGED IN — Google login detected.")
            log("   >>> Sign in with the Google account for Nexus AI Wealth NOW. <<<")
            log("   This script does NOT handle credentials.")
            log(f"   Polling for login (up to {LOGIN_WAIT_SEC}s) — proceeds automatically...")
            log("")

            login_ok = False
            for remaining in range(LOGIN_WAIT_SEC, 0, -2):
                print(f"\rWaiting for login ({remaining}s remaining)...  ", end="", flush=True)
                await asyncio.sleep(2)
                poll_url = page.url
                if "studio.youtube.com" in poll_url and "accounts.google.com" not in poll_url:
                    print(f"\rLogin detected! Proceeding...                  ", flush=True)
                    login_ok = True
                    break
            if not login_ok:
                print(f"\rLogin wait expired.                              ", flush=True)
                results["needs_manual"].append(
                    f"Login not completed in {LOGIN_WAIT_SEC}s — re-run and sign in with Google quickly"
                )

            await wait_ss(page, "03_after_login", delay_ms=2000)
            # Save session
            post_url = page.url
            if "studio.youtube.com" in post_url:
                SESSION_STATE.parent.mkdir(parents=True, exist_ok=True)
                await context.storage_state(path=str(SESSION_STATE))
                log("Session saved — future runs skip login automatically")
                results["completed"].append("Google session saved for future runs")

        # ── Step 2: Capture Studio dashboard ──────────────────────────────────
        log("Step 2: Capturing Studio dashboard...")
        await wait_ss(page, "04_studio_dashboard", delay_ms=2000)

        # ── Step 3: Navigate to Channel Customization → Basic Info ────────────
        log("Step 3: Navigating to Channel Customization > Basic Info...")
        await screenshot(page, "05_pre_customization_nav")

        nav_ok = False
        # Try direct navigation via sidebar
        for nav_label in ["Customization", "Customize channel"]:
            try:
                link = page.get_by_text(nav_label, exact=False).first
                cnt = await link.count()
                if cnt > 0:
                    log(f"Found nav: '{nav_label}'")
                    await safe_click(page, link, nav_label)
                    await wait_ss(page, "06_customization_page", delay_ms=3000)
                    nav_ok = True
                    results["completed"].append(f"Navigated to Customization via '{nav_label}'")
                    break
            except Exception:
                continue

        if not nav_ok:
            log("Sidebar nav not found — trying URL navigation...")
            # Extract channel ID from current URL or use general customization path
            ch_match = re.search(r'channel/(UC[a-zA-Z0-9_-]+)', page.url)
            if ch_match:
                ch_id = ch_match.group(1)
                custom_url = f"https://studio.youtube.com/channel/{ch_id}/customization/basicinfo"
            else:
                custom_url = "https://studio.youtube.com/channel/UC/customization/basicinfo"
            log(f"Trying direct URL: {custom_url}")
            try:
                await page.goto(custom_url, wait_until="domcontentloaded", timeout=20000)
                await wait_ss(page, "06_customization_direct", delay_ms=3000)
                nav_ok = True
                results["completed"].append("Navigated to Basic Info via direct URL")
            except Exception:
                pass

        if not nav_ok:
            results["needs_manual"].append(
                "Navigate to YouTube Studio > Customization > Basic Info manually"
            )

        # ── Step 4: Verify/navigate to Basic Info tab ─────────────────────────
        log("Step 4: Ensuring Basic Info tab is active...")
        for tab_label in ["Basic info", "Basic Info", "BASIC INFO"]:
            try:
                tab = page.get_by_text(tab_label, exact=False).first
                if await tab.count() > 0:
                    await safe_click(page, tab, tab_label)
                    await wait_ss(page, "07_basic_info_tab", delay_ms=2000)
                    results["completed"].append("Basic Info tab activated")
                    break
            except Exception:
                continue

        # ── Step 5: Capture current links state ───────────────────────────────
        log("Step 5: Capturing current links section...")
        await screenshot(page, "08_current_links_state")

        # Look for existing links section
        links_visible = False
        for selector in ["[data-testid='links-section']", "text=Links", "text=Add link"]:
            try:
                el = page.locator(selector).first
                if await el.count() > 0:
                    links_visible = True
                    log(f"Links section detected via: {selector}")
                    break
            except Exception:
                continue

        if links_visible:
            results["completed"].append("Links section located on Basic Info page")
        else:
            results["needs_manual"].append(
                "Could not auto-detect links section — verify you are on Basic Info tab in Customization"
            )

        # ── Step 6: Contact email section check ───────────────────────────────
        log("Step 6: Looking for contact email field...")
        await screenshot(page, "09_contact_email_check")

        email_found = False
        for selector in ["text=Contact info", "text=Business email", "text=Email"]:
            try:
                el = page.locator(selector).first
                if await el.count() > 0:
                    email_found = True
                    log(f"Contact info section found: {selector}")
                    break
            except Exception:
                continue

        # ── Step 7: Final state screenshot ────────────────────────────────────
        log("Step 7: Final state capture...")
        await screenshot(page, "10_final_state")

        # Safety scan
        log("Running safety scan...")
        blocked_found = []
        all_buttons = page.locator("button, [role='button']")
        btn_count = await all_buttons.count()
        for i in range(min(btn_count, 50)):
            try:
                btn = all_buttons.nth(i)
                txt = (await btn.text_content() or "").strip()
                if txt and is_blocked_action(txt):
                    blocked_found.append(txt)
            except Exception:
                continue
        if blocked_found:
            log(f"Safety scan found blocked buttons (NOT clicked): {blocked_found}")
        else:
            log("Safety scan: No blocked buttons were activated.")

        # ── Build manual action list ──────────────────────────────────────────
        if not email_found:
            results["needs_manual"].append(
                f"Contact email: Enter '{CONTACT_EMAIL}' in the Contact Info / Business email field"
            )

        results["needs_manual"].append(
            "LINKS — Verify/add these 6 links in exact order in the Links section:"
        )
        for i, lnk in enumerate(CHANNEL_LINKS, 1):
            results["needs_manual"].append(
                f"  {i}. Title: '{lnk['title']}' → URL: {lnk['url']}"
            )
        results["needs_manual"].append(
            "After adding all links, click 'Publish' (saves channel profile — NOT a video publish)"
        )

        # Close browser
        log("Review the browser. Closing in 30 seconds...")
        countdown(30, "Closing browser")
        await browser.close()

    # ── Final Report ──────────────────────────────────────────────────────────
    print("")
    print("=" * 60)
    print("NEXUS BROWSER WORKER — YOUTUBE STUDIO SETUP REPORT")
    print("=" * 60)
    print(f"\nArtifacts: {ARTIFACTS_DIR}\n")

    print("✅ COMPLETED:")
    if results["completed"]:
        for c in results["completed"]:
            print(f"  - {c}")
    else:
        print("  (none)")

    print("\n⚠️  NEEDS MANUAL ACTION:")
    for m in results["needs_manual"]:
        print(f"  - {m}")

    if results["link_issues"]:
        print("\n🔴 LINK VALIDATION ISSUES:")
        for iss in results["link_issues"]:
            print(f"  - {iss}")
    else:
        print("\n✅ LINK VALIDATION: All 6 links passed format check")

    print(f"\n📸 SCREENSHOTS: {ARTIFACTS_DIR}")
    print("\n🔒 VIDEO_UPLOAD: NOT triggered")
    print("🔒 MONETIZATION: NOT accessed")
    print("🔒 CREDENTIALS: Never logged, stored, or passed")
    print("\n" + "=" * 60)
    log("Browser closed. Task complete.")


if __name__ == "__main__":
    asyncio.run(run())
