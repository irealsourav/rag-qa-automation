const { execSync } = require('child_process')
const path = require('path')
const { defineConfig } = require('cypress')

// UI tests for the demo app (demo_app/). Needs the backend on :3000 and the
// Angular dev server on :4200 (see demo_app/README.md). Run: npm run test:demo-app
module.exports = defineConfig({
  e2e: {
    baseUrl: process.env.CONDUIT_URL || 'http://localhost:4200',
    specPattern: 'tests/e2e/demo_app/**/*.cy.js',
    supportFile: 'tests/e2e/support/demo_app.js',
    fixturesFolder: 'tests/e2e/fixtures',
    screenshotsFolder: 'tests/e2e/screenshots',
    downloadsFolder: 'tests/e2e/downloads',
    video: false,
    retries: { runMode: 1, openMode: 0 },
    setupNodeEvents(on) {
      on('task', {
        // Resets the backend database to the fixed demo data in demo_app/backend/seed.py
        seedDb() {
          const python = process.env.CONDUIT_PYTHON || 'python'
          // Run from the repo root, where `demo_app` is the app package
          const repoRoot = path.resolve(__dirname, '../..')
          execSync(`${python} -m demo_app.backend.seed`, { stdio: 'inherit', cwd: repoRoot })
          return null
        },
      })
    },
  },
})
