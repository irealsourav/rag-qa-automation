const { defineConfig } = require('cypress')

module.exports = defineConfig({
  e2e: {
    baseUrl: process.env.RAG_API_URL || 'http://localhost:8000',
    specPattern: 'cypress/e2e/**/*.cy.js',
    supportFile: false,
    video: false,
    // Claude calls with thinking can take a while
    responseTimeout: 180000,
  },
})
