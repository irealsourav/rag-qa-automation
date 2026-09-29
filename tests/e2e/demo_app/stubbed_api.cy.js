// These tests replace backend responses with cy.intercept, so the UI is checked
// in states that are hard to reach with real data (empty lists, server errors).

describe('UI states with a stubbed API', () => {
  it('shows the empty state when there are no articles', () => {
    cy.intercept('GET', '/api/articles*', { articles: [], articlesCount: 0 }).as('articles')
    cy.visit('/')
    cy.wait('@articles')
    cy.get('.article-preview:not(.empty-feed-message)').should('not.exist')
    cy.get('.empty-feed-message').should('contain', 'No articles are here... yet.')
  })

  it('shows a single page button for one page of results', () => {
    cy.intercept('GET', '/api/articles*', { fixture: 'one-article.json' }).as('articles')
    cy.visit('/')
    cy.wait('@articles')
    cy.get('.article-preview').should('have.length', 1)
    cy.get('.pagination .page-item').should('have.length', 1)
  })

  it('shows the API error when login fails on the server', () => {
    cy.intercept('POST', '/api/users/login', {
      statusCode: 500,
      body: { errors: { server: ['is unavailable'] } },
    }).as('login')
    cy.visit('/login')
    cy.get('input[name="email"]').type('anyone@conduit.test')
    cy.get('input[name="password"]').type('password123')
    cy.get('button[type="submit"]').click()

    cy.wait('@login')
    cy.get('.error-messages').should('contain', 'server is unavailable')
  })
})
