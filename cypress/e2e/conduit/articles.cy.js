describe('Articles', () => {
  it('lists the global feed newest first', () => {
    cy.visit('/')
    cy.get('.article-preview').should('have.length', 5)
    cy.get('.article-preview h1').first().should('have.text', 'Hello Conduit')
    cy.get('.article-preview h1').last().should('have.text', 'Stop using fixed waits in Cypress')
  })

  it('filters by a popular tag', () => {
    cy.visit('/')
    cy.get('.sidebar .tag-list').contains('cypress').click()

    cy.location('pathname').should('eq', '/tag/cypress')
    cy.get('.feed-toggle .nav-link.active').should('contain', 'cypress')
    cy.get('.article-preview').should('have.length', 2)
  })

  it('opens an article and renders its markdown body', () => {
    cy.visit('/article/stop-using-fixed-waits-in-cypress')
    cy.get('.article-page h1').should('have.text', 'Stop using fixed waits in Cypress')
    cy.get('.article-content code').should('contain', 'cy.intercept')
  })

  it('publishes a new article with tags', () => {
    cy.loginAs('carol')
    cy.visit('/editor')
    cy.get('input[name="title"]').type('Testing with seeded data')
    cy.get('input[name="description"]').type('Why every test starts from a known state')
    cy.get('textarea[name="body"]').type('Reset the database before each test.')
    cy.get('input[placeholder="Enter tags"]').type('testing{enter}qa{enter}')
    cy.contains('button', 'Publish Article').click()

    cy.location('pathname').should('eq', '/article/testing-with-seeded-data')
    cy.get('.article-page h1').should('have.text', 'Testing with seeded data')
    cy.get('.tag-list').should('contain', 'testing').and('contain', 'qa')
  })

  it('lets the author edit their article', () => {
    cy.loginAs('alice')
    cy.visit('/article/what-to-test-first')
    cy.contains('a', 'Edit Article').first().click()
    cy.get('input[name="title"]').clear().type('What to test first (updated)')
    cy.contains('button', 'Publish Article').click()

    cy.get('.article-page h1').should('have.text', 'What to test first (updated)')
  })

  it('lets the author delete their article', () => {
    cy.loginAs('carol')
    cy.visit('/article/hello-conduit')
    cy.contains('button', 'Delete Article').first().click()

    cy.location('pathname').should('eq', '/')
    cy.get('.article-preview').should('have.length', 4)
  })

  it('hides edit and delete on someone else\'s article', () => {
    cy.loginAs('alice')
    cy.visit('/article/angular-signals-in-practice')
    cy.get('.article-page h1').should('be.visible')
    cy.contains('Edit Article').should('not.exist')
    cy.contains('Delete Article').should('not.exist')
  })
})
