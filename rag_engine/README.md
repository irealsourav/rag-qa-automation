# rag_engine — the AI tool

The RAG engine reads your sources, turns them into searchable knowledge, and uses that
knowledge with Claude to do testing work:

```
sources/          →   knowledge_base/          →   features/
read each input       shared tools to split,       use the knowledge + Claude
(one folder each)     embed, store and search      to do testing work
```

## sources/ — one folder per source

Everything about one source lives in its folder, so a new source (Cypress, API specs,
Playwright, ...) is a new folder that does not touch the others.

| Folder | Reads | Files |
|---|---|---|
| `jira/` | Jira tickets: stories, bugs, acceptance criteria | `client.py` (talks to the Jira API), `loader.py` (reads tickets), `index.py` (one chunk per ticket → the `jira` collection), `retriever.py` (finds the most similar tickets) |
| `confluence/` | Confluence pages | `loader.py` |
| `test_code/` | Existing test files: Cypress, pytest, Java | `loader.py` |
| `test_reports/` | JUnit XML test results, to spot flaky tests | `loader.py` |

Only `jira/` has its own `index.py` and `retriever.py` so far (Path A of the
[design](../docs/rag-design.md)). The other sources still go through the shared store below.

## knowledge_base/ — shared tools

| File | What it does |
|---|---|
| `langchain_store.py` | `get_store("jira")`: a ChromaDB collection per source, all using the same embedding model. New sources use this |
| `chunker.py`, `embedder.py`, `vectorstore.py` | The original hand-built pipeline (split → embed → store), still used by the features |

Both exist side by side on purpose: the features run on the original pipeline today, and
move to per-source collections one source at a time.

## features/ — what the assistant does

`test_generator.py`, `codebase_qa.py`, `flaky_detector.py`, `coverage_analyzer.py`,
`jira_publisher.py`. `llm_utils.py` holds a small helper for reading Claude's replies.

## Other files

| File | What it does |
|---|---|
| `cli.py` | The command line (`python -m rag_engine ...`) |
| `api.py` | The same features as a REST API |
| `config.py` | Settings, read from `.env` |

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env        # add ANTHROPIC_API_KEY; Jira settings are optional
```

## Command line

```bash
python -m rag_engine ingest [jira|confluence|codebase|test_results|all]
python -m rag_engine generate "feature description" --framework Cypress --count 5
python -m rag_engine ask "your question about the test code"
python -m rag_engine flaky --top-n 10
python -m rag_engine coverage --feature-area "payments"
python -m rag_engine jira-push QA-12 --count 5 [--dry-run]
python -m rag_engine serve                      # start the REST API on :8000
```

With the example data:

```bash
python -m rag_engine ingest codebase --codebase-path sample_data/cypress_tests
python -m rag_engine ingest test_results --results-path sample_data/test_reports
python -m rag_engine ask "which checkout tests use fixed waits?"
TEST_RESULTS_PATH=sample_data/test_reports python -m rag_engine flaky
```

## Jira retriever + eval (Path A)

A Jira-only retrieval layer built with LangChain, following
[docs/rag-design.md](../docs/rag-design.md). One chunk per ticket (title, description and
acceptance criteria), with metadata (`source`, `ticket_id`, `type`, `feature`, `created`)
for filtering.

| File | What it does |
|---|---|
| `sources/jira/index.py` | Loads tickets, makes one chunk per ticket, stores them in the `jira` collection |
| `sources/jira/retriever.py` | `retrieve(query, k, feature=None)`: the most similar tickets |
| `knowledge_base/langchain_store.py` | The shared store and embedding model both of them use |

```bash
python -m rag_engine.sources.jira.index      # 18 sample tickets (or --from-jira)
python -m rag_engine.sources.jira.retriever "how is a failed login handled?"
```

How well it works is measured by the retrieval eval in [`tests/evals/`](../tests/README.md#evals).

## Jira integration

Works with plain Jira Cloud; no test-management plugin is needed.

1. Create an API token at https://id.atlassian.com/manage-profile/security/api-tokens
2. In `.env` set `JIRA_URL` (e.g. `https://yoursite.atlassian.net`), `JIRA_EMAIL`,
   `JIRA_TOKEN` and `JIRA_PROJECT_KEY`
3. Read stories in: `python -m rag_engine ingest jira`
4. Create test cases for a story:

```bash
python -m rag_engine jira-push QA-12 --count 5 --dry-run   # preview only
python -m rag_engine jira-push QA-12 --count 5             # create the issues
```

Each test case becomes a `Task` (change with `JIRA_TEST_ISSUE_TYPE`) with the steps and
expected result in the description, the labels `ai-generated-test` and its category
(`happy-path`, `edge-case`, `negative`), and a `Relates` link to the story. Issues with the
`ai-generated-test` label are skipped by `ingest jira`, so generated tests are never read
back in as requirements.

## REST API

Start it with `python -m rag_engine serve`.

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
