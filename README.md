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

- **LLM**: Claude Sonnet 4.5 (Anthropic)
- **Vector store**: ChromaDB (local, persistent)
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2 (local, free)
- **API**: FastAPI + Uvicorn
- **CLI**: Typer + Rich
