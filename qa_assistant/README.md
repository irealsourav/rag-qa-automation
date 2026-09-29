# qa_assistant — the AI tool

The assistant works in three steps, and each step has its own folder:

```
sources/          →   knowledge_base/          →   features/
read the inputs       split, embed, store,         use the knowledge + Claude
                      search (the "R" in RAG)      to do testing work
```

| Folder / file | What's inside |
|---|---|
| `sources/` | Readers for each input: Jira (`jira_loader.py`, with `jira_client.py` for the Jira API), Confluence, test code (`codebase_loader.py`) and JUnit test reports (`test_results_loader.py`) |
| `knowledge_base/` | Turns text into searchable knowledge. `chunker.py` splits text, `embedder.py` turns it into vectors, `vectorstore.py` stores and searches them in ChromaDB. The `jira_*` and `build_jira_index.py` files are the newer LangChain-based Jira retriever (see below) |
| `features/` | The things the assistant does: `test_generator.py`, `codebase_qa.py`, `flaky_detector.py`, `coverage_analyzer.py`, `jira_publisher.py` |
| `cli.py` | The command line (`python -m qa_assistant ...`) |
| `api.py` | The same features as a REST API |
| `config.py` | Settings, read from `.env` |

Two implementations of the knowledge base live side by side on purpose: the original
hand-built one (`chunker.py`, `embedder.py`, `vectorstore.py`) used by the features, and the
LangChain-based Jira retriever from [Path A of the design](../docs/rag-design.md). The plan
is to move the features onto the new one source by source.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env        # add ANTHROPIC_API_KEY; Jira settings are optional
```

## Command line

```bash
python -m qa_assistant ingest [jira|confluence|codebase|test_results|all]
python -m qa_assistant generate "feature description" --framework Cypress --count 5
python -m qa_assistant ask "your question about the test code"
python -m qa_assistant flaky --top-n 10
python -m qa_assistant coverage --feature-area "payments"
python -m qa_assistant jira-push QA-12 --count 5 [--dry-run]
python -m qa_assistant serve                      # start the REST API on :8000
```

With the example data:

```bash
python -m qa_assistant ingest codebase --codebase-path sample_data/cypress_tests
python -m qa_assistant ingest test_results --results-path sample_data/test_reports
python -m qa_assistant ask "which checkout tests use fixed waits?"
TEST_RESULTS_PATH=sample_data/test_reports python -m qa_assistant flaky
```

## Jira retriever + eval (Path A)

A Jira-only retrieval layer built with LangChain, following
[docs/rag-design.md](../docs/rag-design.md). One chunk per ticket (title, description and
acceptance criteria), with metadata (`source`, `ticket_id`, `type`, `feature`, `created`)
for filtering.

| File | What it does |
|---|---|
| `knowledge_base/jira_store.py` | Shared settings: the `jira` Chroma collection and the embedding model |
| `knowledge_base/build_jira_index.py` | Loads tickets, makes one chunk per ticket, stores them |
| `knowledge_base/jira_retriever.py` | `retrieve(query, k, feature=None)`: the most similar tickets |

```bash
python -m qa_assistant.knowledge_base.build_jira_index      # 18 sample tickets (or --from-jira)
python -m qa_assistant.knowledge_base.jira_retriever "how is a failed login handled?"
```

How well it works is measured by the retrieval eval in [`tests/evals/`](../tests/README.md#evals).

## Jira integration

Works with plain Jira Cloud; no test-management plugin is needed.

1. Create an API token at https://id.atlassian.com/manage-profile/security/api-tokens
2. In `.env` set `JIRA_URL` (e.g. `https://yoursite.atlassian.net`), `JIRA_EMAIL`,
   `JIRA_TOKEN` and `JIRA_PROJECT_KEY`
3. Read stories in: `python -m qa_assistant ingest jira`
4. Create test cases for a story:

```bash
python -m qa_assistant jira-push QA-12 --count 5 --dry-run   # preview only
python -m qa_assistant jira-push QA-12 --count 5             # create the issues
```

Each test case becomes a `Task` (change with `JIRA_TEST_ISSUE_TYPE`) with the steps and
expected result in the description, the labels `ai-generated-test` and its category
(`happy-path`, `edge-case`, `negative`), and a `Relates` link to the story. Issues with the
`ai-generated-test` label are skipped by `ingest jira`, so generated tests are never read
back in as requirements.

## REST API

Start it with `python -m qa_assistant serve`.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Status and number of stored chunks per collection |
| POST | `/generate-tests` | Generate test cases for a feature |
| POST | `/ask` | Ask a question about the test code |
| POST | `/detect-flaky` | Analyse one flaky test |
| GET | `/detect-flaky/all` | Find and analyse all flaky tests |
| POST | `/coverage` | Find coverage gaps |
| POST | `/jira/push-tests` | Generate test cases for a story and create them in Jira |
| POST | `/ingest` | Start loading a source in the background |

```bash
curl -X POST http://localhost:8000/generate-tests \
  -H "Content-Type: application/json" \
  -d '{"feature": "user login with 2FA", "framework": "Cypress", "count": 5}'
```

## Model

Claude Sonnet 5 by default; set `LLM_MODEL` in `.env` to change it. Embeddings use the
local `all-MiniLM-L6-v2` model (no API key, downloaded once, about 80 MB).
