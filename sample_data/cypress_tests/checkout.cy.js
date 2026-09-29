// Sample Cypress suite used by the RAG demo. Some patterns here are intentionally flaky.
describe('Checkout', () => {
  beforeEach(() => {
    cy.login('buyer@example.com', 'secret')
    cy.visit('/cart')
  })

  it('applies a discount code', () => {
    cy.get('[data-cy=discount-input]').type('SAVE10')
    cy.get('[data-cy=apply-discount]').click()
    cy.wait(2000) // fixed sleep instead of waiting on the /api/discount request
    cy.get('[data-cy=total]').should('contain', '$90.00')
  })

  it('completes payment with a saved card', () => {
    cy.get('[data-cy=checkout]').click()
    cy.get('.card-list li').first().click() // order of saved cards is not guaranteed
    cy.get('[data-cy=pay-now]').click()
    cy.contains('Payment successful', { timeout: 4000 })
  })

  it('shows an error for an expired card', () => {
    cy.intercept('POST', '/api/payments', { statusCode: 402, body: { error: 'card_expired' } })
    cy.get('[data-cy=checkout]').click()
    cy.get('[data-cy=pay-now]').click()
    cy.get('[data-cy=payment-error]').should('have.text', 'Your card has expired')
  })
})
