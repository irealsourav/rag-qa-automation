const { execSync } = require('child_process')
const { defineConfig } = require('cypress')

// UI tests for the Conduit demo app (demo_app/). Needs the backend on :3000 and
// the Angular dev server on :4200 (see README "Demo app").
module.exports = defineConfig({
  e2e: {
    baseUrl: process.env.CONDUIT_URL || 'http://localhost:4200',
    specPattern: 'cypress/e2e/conduit/**/*.cy.js',
    supportFile: 'cypress/support/conduit.js',
    video: false,
    retries: { runMode: 1, openMode: 0 },
    setupNodeEvents(on) {
      on('task', {
        // Resets the backend database to the fixed demo data in demo_app/backend/seed.py
        seedDb() {
          const python = process.env.CONDUIT_PYTHON || 'python'
          execSync(`${python} -m demo_app.backend.seed`, { stdio: 'inherit' })
          return null
        },
      })
    },
  },
})
