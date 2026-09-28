// End-to-end tests for the RAG API, run against data ingested from sample_data/.
//
// Claude's wording changes from run to run, so these tests never compare exact text.
// They check what must hold every time: response shape, grounding in the indexed
// files, honest "not found" answers, and a pass rate across repeated runs.

const ask = (question) =>
  cy.request('POST', '/ask', { question, reset_history: true }).its('body.answer')

const NOT_FOUND = /not (found|present|included|shown|in the (provided )?(context|code|codebase))|no (relevant|information|tests?|mention|evidence)|(doesn't|does not|don't|do not) (contain|include|appear|see|have)|(can't|cannot|unable to) find/i

describe('RAG API', () => {
  it('has indexed the sample data', () => {
    cy.request('/health').its('body.collections').then((c) => {
      expect(c.codebase, 'codebase chunks').to.be.greaterThan(0)
      expect(c.test_results, 'test result chunks').to.be.greaterThan(0)
    })
  })

  describe('non-deterministic output', () => {
    it('generate-tests returns the requested structure, not exact text', () => {
      const count = 3
      cy.request('POST', '/generate-tests', {
        feature: 'applying a discount code at checkout',
        framework: 'Cypress',
        count,
      }).then(({ status, body }) => {
        expect(status).to.eq(200)
        const ids = new Set(body.test_cases.match(/TC-\d+/g) || [])
        expect(ids.size, 'distinct TC ids').to.be.within(count - 1, count + 1)
        expect(body.test_cases).to.match(/expected result/i)
        expect(body.test_cases).to.match(/discount/i)
      })
    })

    it('answers are grounded in a file that really exists', () => {
      ask('Which Cypress spec file tests applying a discount code?')
        .should('include', 'checkout.cy.js')
    })

    it('stays consistent across repeated runs', () => {
      const runs = Cypress.env('CONSISTENCY_RUNS')
      let hits = 0
      Cypress._.times(runs, () => {
        ask('Which Cypress spec file tests the login flow?').then((answer) => {
          if (answer.includes('login.cy.js')) hits += 1
        })
      })
      cy.then(() => {
        expect(hits / runs, `${hits}/${runs} runs named login.cy.js`).to.be.at.least(0.66)
      })
    })

    it('says so when the answer is not in the codebase', () => {
      ask('How are the Kubernetes Helm charts tested in this codebase?')
        .should('match', NOT_FOUND)
    })
  })

  describe('flaky detection', () => {
    it('finds the flaky tests (deterministic) and explains them (non-deterministic)', () => {
      cy.request({ url: '/detect-flaky/all?top_n=5', timeout: 600000 })
        .its('body.flaky_tests')
        .then((flaky) => {
          // Detection is plain counting over the JUnit files, so assert exactly
          const byName = Cypress._.keyBy(flaky, 'test_name')
          expect(Object.keys(byName)).to.have.members([
            'applies a discount code',
            'completes payment with a saved card',
            'logs in with valid credentials',
          ])
          Object.values(byName).forEach((t) => expect(t.flaky_score).to.be.closeTo(1 / 3, 0.01))

          // The explanation comes from Claude, so assert on the idea, not the wording
          expect(byName['applies a discount code'].analysis)
            .to.match(/cy\.wait|fixed (wait|delay|sleep|timeout)|hard-?coded (wait|delay|sleep)|intercept/i)
        })
    })
  })
})
