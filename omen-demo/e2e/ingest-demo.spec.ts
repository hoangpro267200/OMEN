import { test, expect } from './fixtures/demo-page';

test.describe('Ingest Demo', () => {
  test('ingest demo page loads', async ({ page }) => {
    await page.goto('/ingest-demo');
    await expect(page.getByRole('main')).toBeVisible({ timeout: 15_000 });
  });

  test('can open ingest demo from nav', async ({ demoPage }) => {
    await demoPage.getByRole('link', { name: /ingest demo/i }).first().click();
    await expect(demoPage).toHaveURL(/\/ingest-demo/);
    await expect(demoPage.getByRole('main')).toBeVisible({ timeout: 10_000 });
  });
});
