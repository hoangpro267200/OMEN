import { test, expect } from './fixtures/demo-page';

test.describe('Partitions', () => {
  test('partitions page loads', async ({ page }) => {
    await page.goto('/partitions');
    await expect(page.getByRole('main')).toBeVisible({ timeout: 15_000 });
  });

  test('partitions page has heading or table or empty state', async ({ page }) => {
    await page.goto('/partitions');
    await page.waitForLoadState('domcontentloaded');
    const main = page.getByRole('main');
    await expect(main).toBeVisible({ timeout: 15_000 });
    const hasHeading = (await main.getByRole('heading').count()) > 0;
    const hasTable = (await main.locator('table').count()) > 0;
    const hasContent = (await main.locator('text=Partition').count()) > 0;
    expect(hasHeading || hasTable || hasContent).toBeTruthy();
  });

  test('can open partitions from nav', async ({ demoPage }) => {
    await demoPage.getByRole('link', { name: /partitions/i }).first().click();
    await expect(demoPage).toHaveURL(/\/partitions/);
    await expect(demoPage.getByRole('main')).toBeVisible({ timeout: 10_000 });
  });
});
