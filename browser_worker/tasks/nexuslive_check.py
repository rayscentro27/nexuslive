"""
Nexuslive health check — opens the site, checks page title, pricing, and signup form.
Uses real browser so JS rendering is validated.
"""
import asyncio


NEXUSLIVE_URL = "https://nexuslive.netlify.app"


async def run(page, payload: dict) -> dict:
    url = payload.get("url", NEXUSLIVE_URL)
    results = []
    errors = []

    try:
        # Load homepage
        response = await page.goto(url, wait_until="networkidle", timeout=30000)
        status = response.status if response else 0
        title = await page.title()
        results.append(f"Homepage: HTTP {status} — '{title}'")

        # Check for key elements
        checks = [
            ("h1, h2", "hero heading"),
            ("[href*='pricing'], a:has-text('Pricing')", "pricing link"),
            ("button:has-text('Get Started'), a:has-text('Get Started')", "CTA button"),
        ]
        for selector, label in checks:
            try:
                el = page.locator(selector).first
                await el.wait_for(timeout=3000)
                text = await el.text_content()
                results.append(f"  ✓ {label}: '{(text or '').strip()[:40]}'")
            except Exception:
                errors.append(f"  ✗ {label} not found")

        # Screenshot for visual verification
        screenshot = await page.screenshot(full_page=False)
        screenshot_b64 = None
        if screenshot:
            import base64
            screenshot_b64 = base64.b64encode(screenshot).decode()

    except Exception as e:
        errors.append(f"Page load failed: {e}")
        screenshot_b64 = None

    summary = "\n".join(results + errors)
    return {
        "status": "error" if errors and not results else "ok",
        "summary": summary,
        "screenshot_b64": screenshot_b64,
        "errors": errors,
    }
