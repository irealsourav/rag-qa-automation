import { PASSWORD, USERS } from '../support/demo_app'

describe('Authentication', () => {
  it('signs in with valid credentials', () => {
    cy.intercept('POST', '/api/users/login').as('login')
    cy.visit('/login')
    cy.get('h1').should('have.text', 'Sign in')
    cy.get('input[name="email"]').type(USERS.alice)
    cy.get('input[name="password"]').type(PASSWORD)
    cy.get('button[type="submit"]').click()

    cy.wait('@login').its('response.statusCode').should('eq', 200)
    cy.location('pathname').should('eq', '/')
    cy.get('.navbar').should('contain', 'alice')
    cy.window().its('localStorage.jwtToken').should('be.a', 'string')
  })

  it('shows an error for a wrong password', () => {
    cy.visit('/login')
    cy.get('input[name="email"]').type(USERS.alice)
    cy.get('input[name="password"]').type('wrong-password')
    cy.get('button[type="submit"]').click()

    cy.get('.error-messages').should('contain', 'credentials invalid')
    cy.location('pathname').should('eq', '/login')
  })

  it('registers a new user', () => {
    cy.visit('/register')
    cy.get('h1').should('have.text', 'Sign up')
    cy.get('input[name="username"]').type('dave')
    cy.get('input[name="email"]').type('dave@conduit.test')
    cy.get('input[name="password"]').type(PASSWORD)
    cy.get('button[type="submit"]').click()

    cy.location('pathname').should('eq', '/')
    cy.get('.navbar').should('contain', 'dave')
  })

  it('rejects a username that is already taken', () => {
    cy.visit('/register')
    cy.get('input[name="username"]').type('alice')
    cy.get('input[name="email"]').type('another@conduit.test')
    cy.get('input[name="password"]').type(PASSWORD)
    cy.get('button[type="submit"]').click()

    cy.get('.error-messages').should('contain', 'username has already been taken')
  })

  it('logs out from the settings page', () => {
    cy.loginAs('alice')
    cy.visit('/settings')
    cy.contains('button', 'Or click here to logout').click()

    cy.location('pathname').should('eq', '/')
    cy.get('.navbar').should('contain', 'Sign in')
    cy.window().its('localStorage.jwtToken').should('not.exist')
  })
})
