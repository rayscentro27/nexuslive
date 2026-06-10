const { chromium } = require('playwright');

const URL = 'https://nexuslive.netlify.app';
const results = [];

function log(test, status, detail = '') {
  const icon = status === 'PASS' ? '✅' : status === 'FAIL' ? '❌' : '⚠️';
  console.log(`${icon} ${status}: ${test}${detail ? ' — ' + detail : ''}`);
  results.push({ test, status, detail });
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  // Capture console errors
  const consoleErrors = [];
  page.on('console', msg => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
  page.on('pageerror', err => consoleErrors.push(err.message));

  try {
    // 1. Page loads
    const res = await page.goto(URL, { waitUntil: 'networkidle', timeout: 20000 });
    log('Page loads', res.status() === 200 ? 'PASS' : 'FAIL', `HTTP ${res.status()}`);

    // 2. New lavender background
    const bg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
    log('Lavender background', bg.includes('234') ? 'PASS' : 'WARN', bg);

    // 3. Pricing page shows (unauthenticated)
    const pricingVisible = await page.locator('text=Plan').first().isVisible({ timeout: 5000 }).catch(() => false);
    log('Pricing page renders (logged out)', pricingVisible ? 'PASS' : 'WARN');

    // 4. Auth button exists
    const authBtn = await page.locator('button, a').filter({ hasText: /sign|login|get started|select/i }).first().isVisible({ timeout: 3000 }).catch(() => false);
    log('Auth/CTA button visible', authBtn ? 'PASS' : 'WARN');

    // 5. No JS console errors
    log('No JS console errors', consoleErrors.length === 0 ? 'PASS' : 'FAIL',
      consoleErrors.length > 0 ? consoleErrors.slice(0, 2).join(' | ') : '');

    // 6. Sidebar not visible when logged out
    const sidebarHidden = !(await page.locator('nav').first().isVisible({ timeout: 2000 }).catch(() => false));
    log('Sidebar hidden when logged out', sidebarHidden ? 'PASS' : 'WARN');

    // 7. Legal link works
    const legalLink = await page.locator('text=/legal|terms|privacy/i').first().isVisible({ timeout: 3000 }).catch(() => false);
    log('Legal link present', legalLink ? 'PASS' : 'WARN');

    // 8. Mobile viewport check
    await page.setViewportSize({ width: 375, height: 812 });
    await page.waitForTimeout(500);
    const mobileOk = await page.locator('body').isVisible();
    log('Mobile viewport renders', mobileOk ? 'PASS' : 'FAIL');

    // Reset to desktop
    await page.setViewportSize({ width: 1280, height: 800 });

    // 9. Navigate to auth page
    const getStarted = page.locator('button').filter({ hasText: /select|get started|choose|start/i }).first();
    if (await getStarted.isVisible({ timeout: 3000 }).catch(() => false)) {
      await getStarted.click();
      await page.waitForTimeout(1000);
      const authForm = await page.locator('input[type="email"], input[placeholder*="email" i]').isVisible({ timeout: 3000 }).catch(() => false);
      log('Auth form loads after CTA click', authForm ? 'PASS' : 'WARN');
    } else {
      log('CTA button click', 'WARN', 'Button not found — skipped');
    }

    // 10. Back to pricing link
    const backBtn = await page.locator('text=/back|pricing/i').first().isVisible({ timeout: 2000 }).catch(() => false);
    log('Back to Pricing link visible', backBtn ? 'PASS' : 'WARN');

  } catch (err) {
    log('Test runner', 'FAIL', err.message);
  } finally {
    await browser.close();

    console.log('\n─────────────────────────────────');
    const passed = results.filter(r => r.status === 'PASS').length;
    const failed = results.filter(r => r.status === 'FAIL').length;
    const warned = results.filter(r => r.status === 'WARN').length;
    console.log(`Results: ${passed} passed | ${failed} failed | ${warned} warnings`);
  }
})();
