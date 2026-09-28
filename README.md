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
python run.py serve
```

## REST API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | System status and document counts |
| POST | `/generate-tests` | Generate test cases for a feature |
| POST | `/ask` | Ask questions about the codebase |
| POST | `/detect-flaky` | Analyse a specific flaky test |
| GET | `/detect-flaky/all` | Detect all flaky tests |
| POST | `/coverage` | Analyse coverage gaps |
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

## Tech stack

- **LLM**: Claude Sonnet 5 (Anthropic), override with `LLM_MODEL` in `.env`
- **Vector store**: ChromaDB (local, persistent)
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2 (local, free)
- **API**: FastAPI + Uvicorn
- **CLI**: Typer + Rich

## Testing

**Unit tests** cover the deterministic parts (chunker, loaders, flaky scoring) and need no API key:

```bash
pip install -r requirements-dev.txt
pytest tests/
```

**Cypress API tests** (`cypress/e2e/rag_api.cy.js`) call the running API, so they use Claude.
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
npx cypress run
```

## GitHub Actions

| Workflow | Trigger | What it does |
|---|---|---|
| `CI` | push / PR to `main` | flake8, import checks, unit tests, API import check. No API key needed |
| `RAG E2E` | manual (Actions -> RAG E2E -> Run workflow) | Ingests `sample_data/`, starts the API, writes Claude's answers to the run's **Summary** page, then runs the Cypress tests |

`RAG E2E` needs an `ANTHROPIC_API_KEY` repository secret
(Settings -> Secrets and variables -> Actions) and uses API credits on every run.
