# RAG QA Automation

An AI-powered QA automation system built on Retrieval-Augmented Generation (RAG).
Uses Claude as the LLM, ChromaDB as the vector store and sentence-transformers for embeddings.

## What it does

| Feature | Description |
|---|---|
| **Test case generation** | Generates Cypress/pytest/Java tests from Jira stories and Confluence docs |
| **Codebase Q&A** | Answer natural language questions about your test codebase |
| **Flaky test detection** | Finds flaky tests from XML reports and suggests root-cause fixes |
| **Coverage gap analysis** | Compares requirements against tests to find what is not covered |
| **Push tests to Jira** | Generates test cases for a Jira story and creates them as linked Jira issues |

The repo also contains a demo application to test: **Conduit**, a Medium-style blog
(Angular frontend + FastAPI backend) in `demo_app/`, with Cypress UI tests.

## Architecture

```
Data Sources → Ingest → Chunk → Embed → ChromaDB
                                           ↓
Query → Retrieve → Claude (LLM) → QA Output
                                           ↓
                          CI/CD | IDE | REST API
```

## Setup

```bash
# 1. Clone and install
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env with your API keys

# 3. Ingest your data
python run.py ingest all

# 4. Start using it
python run.py generate "invoice generation feature"
python run.py ask "where are the login tests?"
python run.py flaky
python run.py coverage --feature-area payments

# Or start the API server
python run.py serve
```

## Try it with the sample data

`sample_data/` holds two small Cypress specs and three JUnit reports with a few tests
that pass in some runs and fail in others:

```bash
python run.py ingest codebase --codebase-path sample_data/codebase
python run.py ingest test_results --results-path sample_data/reports
python run.py ask "which checkout tests use fixed waits?"
TEST_RESULTS_PATH=sample_data/reports python run.py flaky
```

## CLI Commands

```bash
python run.py ingest [jira|confluence|codebase|test_results|all]
python run.py generate "feature description" --framework Cypress --count 5
python run.py ask "your question about the test codebase"
python run.py flaky --top-n 10
python run.py coverage --feature-area "payments"
python run.py jira-push QA-12 --count 5 [--dry-run]
python run.py serve
```

## Jira integration

Works with plain Jira Cloud; no test-management plugin is needed.

1. Create an API token at https://id.atlassian.com/manage-profile/security/api-tokens
2. In `.env` set `JIRA_URL` (e.g. `https://yoursite.atlassian.net`), `JIRA_EMAIL`, `JIRA_TOKEN`
   and `JIRA_PROJECT_KEY`
3. Read stories into the knowledge base: `python run.py ingest jira`
4. Generate test cases for a story and create them in Jira:

```bash
python run.py jira-push QA-12 --count 5 --dry-run   # preview only
python run.py jira-push QA-12 --count 5             # create the issues
```

Each test case becomes a `Task` (set `JIRA_TEST_ISSUE_TYPE` to change it) with the
steps and expected result in the description. It gets the labels `ai-generated-test` and
its category (`happy-path`, `edge-case`, `negative`), and a `Relates` link to the story.
Issues with the `ai-generated-test` label are skipped by `ingest jira`, so generated tests
are never read back in as requirements.

## REST API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | System status and document counts |
| POST | `/generate-tests` | Generate test cases for a feature |
| POST | `/ask` | Ask questions about the codebase |
| POST | `/detect-flaky` | Analyse a specific flaky test |
| GET | `/detect-flaky/all` | Detect all flaky tests |
| POST | `/coverage` | Analyse coverage gaps |
| POST | `/jira/push-tests` | Generate test cases for a story and create them in Jira |
| POST | `/ingest` | Trigger background ingestion |

## Example API calls

```bash
# Generate tests
curl -X POST http://localhost:8000/generate-tests \
  -H "Content-Type: application/json" \
  -d '{"feature": "user login with 2FA", "framework": "Cypress", "count": 5}'

# Ask about codebase
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How is API mocking set up in our Cypress tests?"}'

# Coverage analysis
curl -X POST http://localhost:8000/coverage \
  -H "Content-Type: application/json" \
  -d '{"feature_area": "payment processing"}'
```

## Demo app (Conduit)

`demo_app/frontend` is the [RealWorld Angular app](https://github.com/realworld-apps/angular-realworld-example-app)
(MIT, see `demo_app/frontend/LICENSE`). `demo_app/backend` is a FastAPI + SQLite implementation of the
[RealWorld API spec](https://realworld.show) written for this repo; it passes the official RealWorld
API conformance suite, which CI runs on every push.

```bash
pip install -r demo_app/backend/requirements.txt
python -m demo_app.backend.seed                                # reset to the demo data
python -m uvicorn demo_app.backend.main:app --port 3000 &      # API on :3000

cd demo_app/frontend && npm ci && npm start                    # app on http://localhost:4200
```

Seeded accounts (password `password123`): `alice@conduit.test`, `bob@conduit.test`, `carol@conduit.test`.

## Tech stack

- **LLM**: Claude Sonnet 5 (Anthropic), override with `LLM_MODEL` in `.env`
- **Vector store**: ChromaDB (local, persistent)
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2 (local, free)
- **API**: FastAPI + Uvicorn
- **CLI**: Typer + Rich

## Testing

**Unit tests** cover the deterministic parts (chunker, loaders, flaky scoring, Jira client,
demo backend) and need no API key or Jira account:

```bash
pip install -r requirements-dev.txt -r demo_app/backend/requirements.txt
pytest tests/
```

**Cypress UI tests** for the demo app (`cypress/e2e/conduit/`) reset the database before every
test, so they always start from the same data. `stubbed_api.cy.js` shows `cy.intercept`
replacing API responses to reach states like an empty feed or a server error.

```bash
# with the backend (:3000) and frontend (:4200) running, see "Demo app"
npm ci
npm run cy:conduit
```

If Cypress fails with `bad option: --no-sandbox` in a VS Code terminal, run
`unset ELECTRON_RUN_AS_NODE` first (VS Code sets it, and it stops Cypress from starting).

**Cypress API tests** for the RAG tool (`cypress/e2e/rag/rag_api.cy.js`) call the running API, so they use Claude.
Claude's answers change from run to run, so the tests don't compare exact text. They check:

- response structure (e.g. the requested number of `TC-N` test cases)
- grounding: answers name files that really exist in the index
- honest "not found" answers for things that were never indexed
- a minimum pass rate when the same question is asked several times
- exact results where the output is deterministic (which tests are flaky and their scores)

```bash
# with the sample data ingested (see above)
TEST_RESULTS_PATH=sample_data/reports python -m uvicorn api.main:app --port 8000 &
npm ci
npm run cy:rag
```

## GitHub Actions

| Workflow | Trigger | What it does |
|---|---|---|
| `CI` | push / PR to `main` | flake8, import checks, unit tests, API import check, and for the demo app: frontend unit tests and build, the RealWorld API conformance suite, and the Cypress UI tests. No API key needed |
| `RAG E2E` | manual (Actions -> RAG E2E -> Run workflow) | Ingests `sample_data/`, starts the API, writes Claude's answers to the run's **Summary** page, then runs the Cypress tests |

`RAG E2E` needs an `ANTHROPIC_API_KEY` repository secret
(Settings -> Secrets and variables -> Actions) and uses API credits on every run.
