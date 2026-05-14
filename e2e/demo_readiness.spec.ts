import { test, expect } from '@playwright/test';

const SCREENSHOTS = '/Users/raymonddavis/nexuslive/reports/browser_qa_screenshots';

test.describe('Nexus Demo Readiness - Production QA', () => {

  test('homepage loads without error', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);
    await page.screenshot({ path: `${SCREENSHOTS}/01_homepage.png` });
    const bodyText = await page.textContent('body');
    expect(bodyText).not.toContain('404');
    expect(bodyText).not.toContain('Application error');
  });

  test('login page is accessible', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `${SCREENSHOTS}/02_login.png` });
    const bodyText = await page.textContent('body');
    expect(bodyText).not.toContain('404');
  });

  test('invite URL is accessible', async ({ page }) => {
    await page.goto('/?invited=true&email=rayscentro%40yahoo.com');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);
    await page.screenshot({ path: `${SCREENSHOTS}/03_invite_url.png` });
    const bodyText = await page.textContent('body');
    expect(bodyText).not.toContain('404');
  });

  test('no horizontal overflow on desktop 1280px', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(1500);
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    const clientWidth = await page.evaluate(() => document.documentElement.clientWidth);
    expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 5);
  });

  test('no horizontal overflow on mobile 375px', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);
    await page.screenshot({ path: `${SCREENSHOTS}/04_mobile_375.png` });
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    const clientWidth = await page.evaluate(() => document.documentElement.clientWidth);
    expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 10);
  });

  test('page has valid meta title (SEO)', async ({ page }) => {
    await page.goto('/');
    const title = await page.title();
    expect(title).toBeTruthy();
    expect(title.length).toBeGreaterThan(5);
  });

  test('page loads within 10 seconds', async ({ page }) => {
    const start = Date.now();
    await page.goto('/');
    await page.waitForLoadState('load');
    const elapsed = Date.now() - start;
    expect(elapsed).toBeLessThan(10_000);
  });

});

test.describe('Mobile viewport QA', () => {

  test.use({ viewport: { width: 375, height: 812 } });

  test('mobile: login page renders without overflow', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `${SCREENSHOTS}/05_mobile_login.png` });
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(scrollWidth).toBeLessThanOrEqual(385);
  });

  test('mobile: landing renders without overflow', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `${SCREENSHOTS}/06_mobile_landing.png` });
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(scrollWidth).toBeLessThanOrEqual(385);
  });

});
