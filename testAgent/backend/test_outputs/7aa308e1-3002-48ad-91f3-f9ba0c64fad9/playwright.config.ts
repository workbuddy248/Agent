
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: 'test_outputs/7aa308e1-3002-48ad-91f3-f9ba0c64fad9',
  outputDir: 'test_outputs/7aa308e1-3002-48ad-91f3-f9ba0c64fad9/test-results',
  
  // Test timeout
  timeout: 30000,
  
  // Expect timeout
  expect: {
    timeout: 10000
  },
  
  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: !!process.env.CI,
  
  // Retry on CI only
  retries: process.env.CI ? 2 : 0,
  
  // Reporter to use
  reporter: [
    ['html', { outputFolder: 'test_outputs/7aa308e1-3002-48ad-91f3-f9ba0c64fad9/html-report' }],
    ['json', { outputFile: 'test_outputs/7aa308e1-3002-48ad-91f3-f9ba0c64fad9/results.json' }]
  ],
  
  // Global setup
  use: {
    // Base URL
    baseURL: process.env.CLUSTER_URL,
    
    // Global timeout
    actionTimeout: 15000,
    navigationTimeout: 30000,
    
    // Screenshots and videos
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    
    // Trace
    trace: 'retain-on-failure',
  },
  
  // Browser projects
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  
  // Web Server (if needed)
  // webServer: {
  //   command: 'npm run start',
  //   port: 3000,
  // },
});
