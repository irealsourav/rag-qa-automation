const { defineConfig } = require('cypress')

// API tests for the QA assistant's REST API (qa_assistant/api.py). These call Claude.
// Run: npm run test:qa-assistant
module.exports = defineConfig({
  e2e: {
    baseUrl: process.env.RAG_API_URL || 'http://localhost:8000',
    specPattern: 'tests/e2e/qa_assistant_api/**/*.cy.js',
    supportFile: false,
    fixturesFolder: false,
    screenshotsFolder: 'tests/e2e/screenshots',
    downloadsFolder: 'tests/e2e/downloads',
    video: false,
    // Claude calls with thinking can take a while
    responseTimeout: 180000,
  },
})
