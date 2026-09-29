# sample_data — example inputs

Made-up data so everything can be tried without access to a real company's systems.
All of it is about the [demo app](../demo_app/README.md).

| Folder | What's inside | Used by |
|---|---|---|
| `jira/tickets.json` | 18 Jira-style tickets (stories and bugs) with acceptance criteria | The Jira retriever and its eval |
| `cypress_tests/` | Two Cypress test files, with some deliberately flaky habits (fixed waits) | `ask` questions, flaky-test analysis |
| `test_reports/` | Three JUnit reports of the same tests. Some tests pass in one run and fail in another, which is what makes them flaky | The flaky-test detector |
