// Sample Cypress suite used by the RAG demo.
describe('Login', () => {
  it('logs in with valid credentials', () => {
    cy.visit('/login')
    cy.get('[data-cy=email]').type('user@example.com')
    cy.get('[data-cy=password]').type('correct-horse')
    cy.get('[data-cy=submit]').click()
    cy.url().should('include', '/dashboard')
  })

  it('rejects an invalid password', () => {
    cy.intercept('POST', '/api/login', { statusCode: 401 }).as('login')
    cy.visit('/login')
    cy.get('[data-cy=email]').type('user@example.com')
    cy.get('[data-cy=password]').type('wrong')
    cy.get('[data-cy=submit]').click()
    cy.wait('@login')
    cy.get('[data-cy=login-error]').should('be.visible')
  })
})
