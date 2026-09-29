# tests — everything that checks quality

| Folder | What it checks | Needs |
|---|---|---|
| `unit/` | Small, fast checks of individual pieces of Python code | Nothing (no AI, no internet) |
| `e2e/demo_app/` | The demo website in a real browser, like a user would use it (Cypress) | Demo app running |
| `e2e/qa_assistant_api/` | The AI assistant's REST API, including its AI answers (Cypress) | Assistant running, Claude API key |
| `evals/` | How good the AI's retrieval is, as a score | Embedding model (downloaded once) |

## Unit tests

```bash
pip install -r requirements.txt -r requirements-dev.txt -r demo_app/backend/requirements.txt
pytest tests/unit
```

## Browser tests of the demo app

Start the demo app first (see [demo_app/README.md](../demo_app/README.md)), then:

```bash
npm ci
npm run test:demo-app
```

Every test resets the demo data first, so tests never depend on each other.
`stubbed_api.cy.js` replaces server responses with `cy.intercept`, to test screens that are
hard to reach with real data (an empty feed, a server error).

If Cypress fails with `bad option: --no-sandbox` in a VS Code terminal, run
`unset ELECTRON_RUN_AS_NODE` first. VS Code sets that variable and it stops Cypress starting.

## API tests of the AI assistant

The AI gives different wording every time, so these tests never compare exact text.
They check things that must be true every time:

- the response has the right structure (for example, the requested number of test cases)
- answers name files that really exist in the data (grounding)
- questions about things that were never loaded get an honest "not found"
- asking the same question several times gives the right answer most of the time
- exact results where the output does not come from the AI (which tests are flaky)

```bash
python -m qa_assistant ingest codebase --codebase-path sample_data/cypress_tests
python -m qa_assistant ingest test_results --results-path sample_data/test_reports
TEST_RESULTS_PATH=sample_data/test_reports python -m uvicorn qa_assistant.api:app --port 8000 &
npm ci
npm run test:qa-assistant
```

These call Claude, so they need `ANTHROPIC_API_KEY` and cost API credits.

## Evals

An eval is a regression test for an AI system: a list of questions with known right
answers, plus a score. `evals/eval_retrieval.py` asks 18 questions and checks whether the
Jira retriever finds the right ticket.

```bash
python -m qa_assistant.knowledge_base.build_jira_index
python -m tests.evals.eval_retrieval --min-hit-at-k 0.9 --min-mrr 0.85
```

| Score | Meaning |
|---|---|
| hit@1 | The right ticket came first |
| hit@3 | The right ticket was in the top 3 |
| MRR | 1 point for 1st place, ½ for 2nd, ⅓ for 3rd, averaged |

Current result on the sample data: hit@1 100%, hit@3 100%, MRR 1.00. A simple
keyword-matching search scores only 50% hit@1 on the same questions, so the eval does
separate real meaning-based search from word matching. The tickets and questions were
written together, so real tickets and real questions are needed before these numbers mean
much. CI runs this eval on every push and fails if the scores drop below the thresholds.
