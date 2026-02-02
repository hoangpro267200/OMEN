import { test, expect } from '@playwright/test';

test.describe('Visual Regression', () => {
  test('overview layout', async ({ page }) => {
    test.skip(!!process.env.CI, 'Skipped in CI (no baseline)');
    await page.goto('/');
    await page.waitForLoadState('networkidle').catch(() => {});
    await expect(page.getByRole('main')).toBeVisible({ timeout: 15_000 });
    await expect(page).toHaveScreenshot('overview.png', {
      fullPage: true,
      maxDiffPixels: 200,
    });
  });

  test('signals list', async ({ page }) => {
    test.skip(!!process.env.CI, 'Skipped in CI (no baseline)');
    await page.goto('/signals');
    await page.waitForLoadState('networkidle').catch(() => {});
    await expect(page.getByRole('heading', { name: /signals/i })).toBeVisible({ timeout: 15_000 });
    await expect(page).toHaveScreenshot('signals-list.png', {
      fullPage: true,
      maxDiffPixels: 200,
    });
  });

  test('responsive mobile viewport', async ({ page }) => {
    test.skip(!!process.env.CI, 'Skipped in CI (no baseline)');
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await page.waitForLoadState('networkidle').catch(() => {});
    await expect(page.getByRole('main')).toBeVisible({ timeout: 15_000 });
    await expect(page).toHaveScreenshot('overview-mobile.png', {
      fullPage: true,
      maxDiffPixels: 200,
    });
  });
});
