import { test, expect } from './fixtures/demo-page';

test.describe('Signals', () => {
  test('signals page shows header and main content', async ({ page }) => {
    await page.goto('/signals');
    await expect(page.getByRole('heading', { name: /signals/i })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole('main')).toBeVisible();
  });

  test('signals page has search or table or empty state', async ({ page }) => {
    await page.goto('/signals');
    await page.waitForLoadState('domcontentloaded');
    const main = page.getByRole('main');
    await expect(main).toBeVisible({ timeout: 15_000 });
    const hasSearch = (await main.getByPlaceholder(/search/i).count()) > 0;
    const hasTable = (await main.locator('table').count()) > 0;
    const hasEmpty = (await main.getByText(/no signals found/i).count()) > 0;
    expect(hasSearch || hasTable || hasEmpty).toBeTruthy();
  });

  test('can open signals from nav', async ({ demoPage }) => {
    await demoPage.getByRole('link', { name: /signals/i }).first().click();
    await expect(demoPage).toHaveURL(/\/signals/);
    await expect(demoPage.getByRole('heading', { name: /signals/i })).toBeVisible({ timeout: 10_000 });
  });
});
