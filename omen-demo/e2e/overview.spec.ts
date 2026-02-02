import { test, expect } from './fixtures/demo-page';

test.describe('Overview', () => {
  test('shows overview content on root', async ({ demoPage }) => {
    await expect(demoPage.getByRole('main')).toBeVisible({ timeout: 15_000 });
    // Overview can show KPIs, activity, or loading/error state
    const main = demoPage.locator('#main-content');
    await expect(main).toBeVisible();
  });

  test('overview has visible content or loading state', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle').catch(() => {});
    const main = page.getByRole('main');
    await expect(main).toBeVisible({ timeout: 15_000 });
    const hasContent =
      (await main.getByRole('heading').count()) > 0 ||
      (await main.locator('[class*="skeleton"]').count()) > 0 ||
      (await main.locator('text=Overview').count()) > 0;
    expect(hasContent).toBeTruthy();
  });
});
