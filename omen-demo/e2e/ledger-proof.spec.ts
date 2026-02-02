import { test, expect } from './fixtures/demo-page';

test.describe('Ledger Proof', () => {
  test('ledger proof page loads', async ({ page }) => {
    await page.goto('/ledger-proof');
    await expect(page.getByRole('main')).toBeVisible({ timeout: 15_000 });
  });

  test('can open ledger proof from nav', async ({ demoPage }) => {
    await demoPage.getByRole('link', { name: /ledger proof/i }).first().click();
    await expect(demoPage).toHaveURL(/\/ledger-proof/);
    await expect(demoPage.getByRole('main')).toBeVisible({ timeout: 10_000 });
  });
});
