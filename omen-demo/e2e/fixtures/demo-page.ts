import { test as base } from '@playwright/test';
import type { Page } from '@playwright/test';

/**
 * Demo app has no login. This fixture ensures we start on the app root.
 * Use "page" for unauthenticated flows; use "demoPage" when you want to start at /.
 */
export const test = base.extend<{ demoPage: Page }>({
  demoPage: async ({ page }, use) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    await use(page);
  },
});

export { expect } from '@playwright/test';
