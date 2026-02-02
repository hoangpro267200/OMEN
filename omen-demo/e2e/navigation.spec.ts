import { test, expect } from '@playwright/test';

test.describe('Navigation', () => {
  test('loads app at root', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveURL(/\//);
    await expect(page.getByRole('main')).toBeVisible({ timeout: 15_000 });
  });

  test('sidebar links navigate to all routes', async ({ page }) => {
    await page.goto('/');

    await page.getByRole('link', { name: /overview/i }).first().click();
    await expect(page).toHaveURL('/');
    await expect(page.getByRole('main')).toBeVisible();

    await page.getByRole('link', { name: /partitions/i }).first().click();
    await expect(page).toHaveURL(/\/partitions/);
    await expect(page.getByRole('main')).toBeVisible();

    await page.getByRole('link', { name: /signals/i }).first().click();
    await expect(page).toHaveURL(/\/signals/);
    await expect(page.getByRole('heading', { name: /signals/i })).toBeVisible({ timeout: 10_000 });

    await page.getByRole('link', { name: /ingest demo/i }).first().click();
    await expect(page).toHaveURL(/\/ingest-demo/);
    await expect(page.getByRole('main')).toBeVisible();

    await page.getByRole('link', { name: /ledger proof/i }).first().click();
    await expect(page).toHaveURL(/\/ledger-proof/);
    await expect(page.getByRole('main')).toBeVisible();
  });

  test('main content has skip link target', async ({ page }) => {
    await page.goto('/');
    const main = page.locator('#main-content');
    await expect(main).toBeVisible({ timeout: 15_000 });
  });
});
