const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests',
  workers: 1,
  use: {
    baseURL: 'http://127.0.0.1:18183',
    launchOptions: process.env.BOYS_TEST_BROWSER
      ? { executablePath: process.env.BOYS_TEST_BROWSER }
      : {},
  },
  projects: [
    { name: 'desktop', use: { viewport: { width: 1440, height: 1000 } } },
    { name: 'phone', use: { viewport: { width: 390, height: 844 } } },
  ],
  webServer: {
    command: 'python3 tests/serve.py',
    url: 'http://127.0.0.1:18183/ready',
    reuseExistingServer: false,
  },
});
