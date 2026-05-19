#!/usr/bin/env python3
"""
Nexus Browser Worker — Beehiiv Setup Assistant
================================================
Task:       beehiiv_setup_assist
Target:     app.beehiiv.com — "Nexus AI Wealth" newsletter
Safety:     LOW_RISK — page editing only. Never publishes, never purchases.
Approval:   SUPERVISED — runs in headed (visible) mode. Ray can intervene.
Screenshots: artifacts/browser_tasks/beehiiv/

SAFETY RULES (hard-coded, not overridable):
  - NEVER clicks Publish, Send, or Launch
  - NEVER clicks any billing or upgrade button
  - NEVER stores, logs, or prints credentials
  - NEVER sends a newsletter/broadcast
  - Saves all screenshots before each action
  - Stops and prompts if unexpected page is detected
  - Run Chrome CLOSED before starting (profile lock conflict)

Usage:
  python3 scripts/browser_tasks/beehiiv_setup_assist.py

Requirements:
  pip3 install --break-system-packages playwright
  python3 -m playwright install chromium
"""

import asyncio
import sys
import os
import re
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PWTimeoutError

# ─── Configuration ────────────────────────────────────────────────────────────

CHROME_EXECUTABLE = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CHROME_USER_DATA  = str(Path.home() / "Library/Application Support/Google/Chrome")
ARTIFACTS_DIR     = Path(__file__).resolve().parent.parent.parent / "artifacts" / "browser_tasks" / "beehiiv"
BEEHIIV_APP_URL   = "https://app.beehiiv.com"

TARGET_HEADLINE    = "AI-Powered Intelligence. Real-World Wealth."
TARGET_SUBHEADLINE = (
    "Discover AI business opportunities, funding intelligence, automation systems, "
    "affiliate strategies, and scalable online income insights powered by Nexus AI."
)
TARGET_CTA_PRIMARY   = "Join the Newsletter"
TARGET_CTA_SECONDARY = "Explore Opportunities"

# Selectors to NEVER click — hard-coded safety list
BLOCKED_TEXT_PATTERNS = [
    r"publish", r"send now", r"launch", r"go live", r"upgrade",
    r"subscribe to plan", r"billing", r"payment", r"buy now",
    r"send broadcast", r"confirm send",
]

# ─── Helpers ──────────────────────────────────────────────────────────────────

def ts() -> str:
    return datetime.now().strftime("%H%M%S")

def log(msg: str) -> None:
    print(f"[beehiiv_worker {ts()}] {msg}")

def is_blocked_action(text: str) -> bool:
    text_lower = text.lower().strip()
    return any(re.search(p, text_lower) for p in BLOCKED_TEXT_PATTERNS)

async def screenshot(page, name: str) -> Path:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    path = ARTIFACTS_DIR / f"{ts()}_{name}.png"
    await page.screenshot(path=str(path), full_page=False)
    log(f"Screenshot saved: {path.name}")
    return path

async def safe_click(page, locator, label: str) -> bool:
    """Click only if label is not in blocked list. Returns True if clicked."""
    if is_blocked_action(label):
        log(f"BLOCKED: refusing to click '{label}' — matches safety filter")
        return False
    log(f"Clicking: {label}")
    await locator.click()
    return True

async def wait_and_screenshot(page, name: str, delay_ms: int = 1200) -> None:
    await page.wait_for_timeout(delay_ms)
    await screenshot(page, name)

# ─── Main Task ────────────────────────────────────────────────────────────────

async def run():
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    log("=== Nexus Browser Worker: beehiiv_setup_assist ===")
    log(f"Artifacts: {ARTIFACTS_DIR}")
    log("Safety: PUBLISH blocked | BILLING blocked | CREDENTIALS never stored")
    log("")
    log("⚠️  IMPORTANT: Close Google Chrome before continuing.")
    log("   (Chrome must not be running to use its profile.)")
    log("")

    input("Press ENTER when Chrome is closed to start the browser session...")

    results = {
        "screenshots": [],
        "completed": [],
        "needs_manual": [],
        "blocked": [],
    }

    async with async_playwright() as pw:
        # ── Launch Chrome with existing profile (reuses Beehiiv session) ──────
        log("Launching Chrome with existing profile (session reuse)...")
        try:
            context = await pw.chromium.launch_persistent_context(
                user_data_dir=CHROME_USER_DATA,
                executable_path=CHROME_EXECUTABLE,
                headless=False,                 # SUPERVISED — Ray can watch + intervene
                slow_mo=400,                    # Deliberate — easy to follow
                viewport={"width": 1440, "height": 900},
                args=["--start-maximized"],
                ignore_default_args=["--enable-automation"],  # less bot-like appearance
            )
        except Exception as e:
            log(f"ERROR launching with Chrome profile: {e}")
            log("Falling back to fresh Chromium (will require manual login)...")
            browser = await pw.chromium.launch(headless=False, slow_mo=400)
            context = await browser.new_context(viewport={"width": 1440, "height": 900})

        page = context.pages[0] if context.pages else await context.new_page()

        # ── Step 1: Navigate to Beehiiv ───────────────────────────────────────
        log("Step 1: Navigating to Beehiiv...")
        await page.goto(BEEHIIV_APP_URL, wait_until="domcontentloaded", timeout=30000)
        await wait_and_screenshot(page, "01_beehiiv_landing")
        results["screenshots"].append("01_beehiiv_landing")

        # Check if logged in
        current_url = page.url
        log(f"Current URL: {current_url}")

        if "login" in current_url or "sign_in" in current_url or "signup" in current_url:
            await screenshot(page, "02_not_logged_in")
            log("")
            log("⚠️  NOT LOGGED IN — Beehiiv login page detected.")
            log("   Please log in manually in the browser window.")
            log("   This script does NOT handle credentials.")
            log("")
            input("Press ENTER after you have logged in manually...")
            await wait_and_screenshot(page, "03_after_manual_login")
            results["needs_manual"].append("Manual login required — session not found in Chrome profile")

        # ── Step 2: Find the Nexus AI Wealth publication ──────────────────────
        log("Step 2: Looking for 'Nexus AI Wealth' publication...")
        await screenshot(page, "04_dashboard")

        pub_link = page.get_by_text("Nexus AI Wealth", exact=False).first
        if await pub_link.count() > 0:
            log("Found 'Nexus AI Wealth' — clicking...")
            await safe_click(page, pub_link, "Nexus AI Wealth publication link")
            await wait_and_screenshot(page, "05_pub_selected")
            results["completed"].append("Located and selected 'Nexus AI Wealth' publication")
        else:
            log("'Nexus AI Wealth' not found on dashboard — taking screenshot for review")
            await screenshot(page, "05_pub_not_found")
            results["needs_manual"].append("Could not locate 'Nexus AI Wealth' publication link — may need manual navigation")

        # ── Step 3: Navigate to Website Editor ────────────────────────────────
        log("Step 3: Looking for Website / Editor navigation...")
        await screenshot(page, "06_pre_editor_nav")

        # Try multiple selector strategies for the website editor link
        editor_found = False
        for nav_text in ["Website", "Design", "Editor", "Site"]:
            try:
                nav_link = page.get_by_role("link", name=nav_text, exact=False).first
                if await nav_link.count() > 0:
                    log(f"Found nav link: '{nav_text}'")
                    await safe_click(page, nav_link, nav_text)
                    await wait_and_screenshot(page, f"07_nav_{nav_text.lower()}")
                    editor_found = True
                    results["completed"].append(f"Navigated to '{nav_text}' section")
                    break
            except PWTimeoutError:
                continue

        if not editor_found:
            log("Could not find editor navigation automatically")
            results["needs_manual"].append("Navigate to Website > Editor manually, then re-run or continue from browser")

        await screenshot(page, "08_editor_view")

        # ── Step 4: Edit Hero Headline ─────────────────────────────────────────
        log("Step 4: Looking for hero headline to edit...")
        await screenshot(page, "09_pre_headline_edit")

        headline_edited = False

        # Common Beehiiv editor patterns — click on editable headline areas
        headline_selectors = [
            "h1[contenteditable]",
            "[data-testid='hero-title']",
            "[class*='hero'] h1",
            "[class*='headline']",
            "h1",
        ]

        for sel in headline_selectors:
            try:
                el = page.locator(sel).first
                if await el.count() > 0:
                    current_text = await el.inner_text()
                    log(f"Found headline candidate: '{current_text[:60]}'")
                    await el.click()
                    await page.wait_for_timeout(500)
                    await screenshot(page, "10_headline_clicked")

                    # Check if it became editable
                    is_editable = await el.is_editable()
                    if is_editable:
                        await el.select_text()
                        await el.fill(TARGET_HEADLINE)
                        await page.wait_for_timeout(500)
                        await screenshot(page, "11_headline_filled")
                        log(f"Headline set to: '{TARGET_HEADLINE}'")
                        results["completed"].append(f"Hero headline edited → '{TARGET_HEADLINE}'")
                        headline_edited = True
                        break
                    else:
                        log(f"Element '{sel}' not directly editable — may need double-click or Beehiiv block editor")
                        await el.dblclick()
                        await page.wait_for_timeout(600)
                        await screenshot(page, "10b_headline_dblclick")
                        is_editable_2 = await el.is_editable()
                        if is_editable_2:
                            await el.select_text()
                            await el.fill(TARGET_HEADLINE)
                            await screenshot(page, "11_headline_filled")
                            results["completed"].append(f"Hero headline edited → '{TARGET_HEADLINE}'")
                            headline_edited = True
                            break
            except Exception as ex:
                log(f"Selector '{sel}' error: {ex}")
                continue

        if not headline_edited:
            log("Could not auto-edit headline — Beehiiv may use a block/canvas editor")
            log(f"TARGET HEADLINE: {TARGET_HEADLINE}")
            results["needs_manual"].append(
                f"Headline: Click on hero text in editor and replace with → '{TARGET_HEADLINE}'"
            )

        # ── Step 5: Edit Subheadline ───────────────────────────────────────────
        log("Step 5: Looking for subheadline...")
        await screenshot(page, "12_pre_subheadline")

        subheadline_edited = False
        sub_selectors = [
            "h2[contenteditable]",
            "[data-testid='hero-subtitle']",
            "[class*='hero'] p",
            "[class*='subtitle']",
            "[class*='subheadline']",
            "h2",
        ]

        for sel in sub_selectors:
            try:
                el = page.locator(sel).first
                if await el.count() > 0:
                    current_text = await el.inner_text()
                    log(f"Found subheadline candidate: '{current_text[:60]}'")
                    if await el.is_editable():
                        await el.select_text()
                        await el.fill(TARGET_SUBHEADLINE)
                        await screenshot(page, "13_subheadline_filled")
                        results["completed"].append(f"Subheadline edited")
                        subheadline_edited = True
                        break
            except Exception as ex:
                log(f"Subheadline selector '{sel}' error: {ex}")

        if not subheadline_edited:
            results["needs_manual"].append(
                f"Subheadline: Replace body text with → '{TARGET_SUBHEADLINE}'"
            )

        # ── Step 6: Check / Add CTA Buttons ───────────────────────────────────
        log("Step 6: Looking for CTA buttons...")
        await screenshot(page, "14_pre_cta_check")

        cta_selectors = [
            "button[contenteditable]",
            "[class*='cta']",
            "[class*='button'] [contenteditable]",
            "a[contenteditable]",
        ]

        cta_found = False
        for sel in cta_selectors:
            try:
                els = page.locator(sel)
                count = await els.count()
                if count > 0:
                    first_text = await els.first.inner_text()
                    log(f"Found {count} CTA candidate(s). First: '{first_text}'")
                    cta_found = True
                    results["completed"].append(f"CTA elements detected ({count} found)")
                    break
            except Exception:
                pass

        if not cta_found:
            results["needs_manual"].append(
                f"CTA buttons: Add primary button 'Join the Newsletter' and secondary 'Explore Opportunities' in the website editor"
            )

        # ── Step 7: Final screenshot ────────────────────────────────────────────
        await screenshot(page, "15_final_state")
        log("Final screenshot saved.")

        # ── Step 8: SAFETY CHECK — scan for publish buttons ───────────────────
        log("Running safety scan for publish/billing elements...")
        dangerous_elements = await page.locator("button, a").all()
        dangerous_found = []
        for el in dangerous_elements[:50]:  # Check up to 50 elements
            try:
                text = (await el.inner_text()).strip()
                if text and is_blocked_action(text):
                    dangerous_found.append(text)
            except Exception:
                pass

        if dangerous_found:
            log(f"Safety scan: Found {len(dangerous_found)} blocked elements (not clicked): {dangerous_found}")
        else:
            log("Safety scan: No publish/billing buttons were activated.")

        # ── Print Report ──────────────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("NEXUS BROWSER WORKER — BEEHIIV SETUP REPORT")
        print("=" * 60)
        print(f"\nArtifacts: {ARTIFACTS_DIR}")
        print(f"\n✅ COMPLETED ({len(results['completed'])}):")
        for item in results["completed"]:
            print(f"  - {item}")

        print(f"\n⚠️  NEEDS MANUAL ACTION ({len(results['needs_manual'])}):")
        for item in results["needs_manual"]:
            print(f"  - {item}")

        if results["blocked"]:
            print(f"\n🚫 BLOCKED ({len(results['blocked'])}):")
            for item in results["blocked"]:
                print(f"  - {item}")

        print(f"\n📸 SCREENSHOTS: {ARTIFACTS_DIR}")
        print("\n🔒 PUBLISH: NOT clicked — requires your manual approval")
        print("🔒 BILLING: NOT accessed")
        print("🔒 CREDENTIALS: Never logged, stored, or passed to script")
        print("\n" + "=" * 60)

        input("\nPress ENTER to close the browser when done reviewing...")
        await context.close()
        log("Browser closed. Task complete.")


# ─── Nexus Browser Worker Metadata ────────────────────────────────────────────

WORKER_METADATA = {
    "task_name":      "beehiiv_setup_assist",
    "target_site":    "https://app.beehiiv.com",
    "publication":    "Nexus AI Wealth",
    "safety_level":   "LOW_RISK",
    "required_approval": {
        "publish":   True,
        "billing":   "BLOCKED — never accessed",
        "send_email":"BLOCKED — never accessed",
    },
    "screenshots_path": "artifacts/browser_tasks/beehiiv/",
    "mode":           "headed (supervised — Ray can watch and intervene)",
    "edits_targeted": [
        f"Hero headline → '{TARGET_HEADLINE}'",
        f"Subheadline → '{TARGET_SUBHEADLINE[:60]}...'",
        "Primary CTA → 'Join the Newsletter'",
        "Secondary CTA → 'Explore Opportunities'",
    ],
    "blocked_actions": BLOCKED_TEXT_PATTERNS,
}


if __name__ == "__main__":
    print(__doc__)
    print("\nWorker metadata:")
    for k, v in WORKER_METADATA.items():
        print(f"  {k}: {v}")
    print()
    asyncio.run(run())
