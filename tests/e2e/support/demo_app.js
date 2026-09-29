// Shared setup for the Conduit UI tests.

// Every seeded user has this password (demo_app/backend/seed.py)
export const PASSWORD = 'password123'

export const USERS = {
  alice: 'alice@conduit.test',
  bob: 'bob@conduit.test',
  carol: 'carol@conduit.test',
}

beforeEach(() => {
  cy.task('seedDb')
})

// Logs in through the API and stores the token where the app reads it,
// so tests that are not about the login form skip it.
Cypress.Commands.add('loginAs', (username) => {
  cy.request('POST', '/api/users/login', {
    user: { email: USERS[username], password: PASSWORD },
  }).then(({ body }) => {
    window.localStorage.setItem('jwtToken', body.user.token)
  })
})
