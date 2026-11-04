import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  timeout: 90000,
  expect: { timeout: 20000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: process.env.BROWSER_BASE_URL || 'http://127.0.0.1:15173',
    browserName: 'chromium',
    viewport: { width: 1365, height: 900 },
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
})
