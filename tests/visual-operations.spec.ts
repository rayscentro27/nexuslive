import { test, expect } from '@playwright/test';

const SHOT_DIR = 'reports/final_visual_demo_screenshots';

test('dashboard visual baseline', async ({ page }, testInfo) => {
  await page.goto('/');
  await page.waitForTimeout(2000);
  await expect(page.locator('body')).toBeVisible();
  await page.screenshot({ path: `${SHOT_DIR}/${testInfo.project.name}-dashboard.png`, fullPage: true });
});

test('workforce office/admin visual baseline', async ({ page }, testInfo) => {
  await page.goto('/admin');
  await page.waitForTimeout(2500);
  await expect(page.locator('body')).toBeVisible();
  await page.screenshot({ path: `${SHOT_DIR}/${testInfo.project.name}-admin.png`, fullPage: true });
});
