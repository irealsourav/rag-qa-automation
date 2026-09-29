describe('Favorites, follows and comments', () => {
  it('favorites an article and updates the count', () => {
    cy.loginAs('alice')
    cy.visit('/article/angular-signals-in-practice')
    cy.contains('button', 'Favorite Article').should('contain', '(0)').click()
    cy.contains('button', 'Unfavorite Article').should('contain', '(1)')
  })

  it('shows followed authors in Your Feed', () => {
    cy.loginAs('carol')
    cy.visit('/profile/bob')
    cy.contains('button', 'Follow').click()
    cy.contains('button', 'Unfollow').should('be.visible')

    cy.visit('/?feed=following')
    // carol follows alice (seeded) and now bob
    cy.get('.article-preview .author').then(($authors) => {
      const names = [...$authors].map((a) => a.innerText.trim())
      expect(new Set(names)).to.deep.equal(new Set(['alice', 'bob']))
    })
  })

  it('posts and deletes a comment', () => {
    cy.loginAs('alice')
    cy.visit('/article/writing-stable-selectors')
    cy.get('textarea[placeholder="Write a comment..."]').type('Agreed, data-cy all the way.')
    cy.contains('button', 'Post Comment').click()

    cy.get('.card:not(.comment-form) .card-block').should('have.length', 1)
      .and('contain', 'Agreed, data-cy all the way.')
    cy.get('.mod-options .ion-trash-a').click()
    cy.get('.card:not(.comment-form)').should('not.exist')
  })

  it('does not offer delete on other people\'s comments', () => {
    cy.loginAs('alice')
    cy.visit('/article/stop-using-fixed-waits-in-cypress')
    cy.get('.card:not(.comment-form) .card-block').should('have.length', 2)
    cy.get('.mod-options').should('not.exist')
  })
})
