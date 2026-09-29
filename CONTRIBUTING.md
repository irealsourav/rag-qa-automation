# Contributing to RAG QA Automation

Thanks for your interest in contributing. This document covers how to set up the project locally, the code style guidelines and how to submit a pull request.

---

## Local setup

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USERNAME/rag-qa-automation.git
cd rag-qa-automation

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. Set up environment
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env
```

---

## Branch naming

| Type | Format | Example |
|---|---|---|
| Feature | `feat/short-description` | `feat/add-playwright-loader` |
| Bug fix | `fix/short-description` | `fix/flaky-score-calculation` |
| Docs | `docs/short-description` | `docs/update-readme` |
| Refactor | `refactor/short-description` | `refactor/vectorstore-client` |

Always branch from `main`.

---

## Code style

- **Python 3.10+**
- Follow **PEP 8** — enforced via `flake8`
- Max line length: **100 characters**
- Use **type hints** on all function signatures
- Docstrings on all public classes and methods
- No bare `except:` — always catch specific exceptions

Run linting before committing:
```bash
flake8 . --max-line-length=100 --exclude=venv,chroma_db,node_modules --ignore=E501,W503
```

---

## Project structure

```
rag-qa-automation/
├── rag_engine/         ← the AI tool (RAG engine)
│   ├── sources/        ← one folder per source: jira/, confluence/, test_code/, test_reports/
│   ├── knowledge_base/ ← shared tools: split, embed, store, search
│   ├── features/       ← test generator, Q&A, flaky detector, coverage, Jira push
│   ├── cli.py          ← command line (python -m rag_engine ...)
│   └── api.py          ← REST API
├── demo_app/           ← the website being tested (Angular + FastAPI)
├── tests/              ← unit/, e2e/ (Cypress), evals/
└── sample_data/        ← example tickets, test files and reports
```

Each folder has a README explaining it in plain words.

Adding a new data source (e.g. Cypress, API specs, Playwright)? Create a folder for it in `rag_engine/sources/`, following `sources/jira/`:
- `loader.py` reads the source and returns `List[Dict]` with at minimum `id`, `source`, `content`
- `index.py` splits it by its natural unit (one ticket, one test block, one endpoint), adds metadata and stores it in its own collection with `get_store("<source>")`
- `retriever.py` searches that collection
- add questions for it to `tests/evals/` so its retrieval quality is measured

Adding a new feature? Create a module in `rag_engine/features/` and expose it via both the CLI (`rag_engine/cli.py`) and the API (`rag_engine/api.py`).

---

## Submitting a pull request

1. Make sure your branch is up to date with `main`
2. Write or update tests if relevant
3. Run the unit tests (`pytest tests/unit`) and linting (see above)
4. Commit with a clear message (see below)
5. Open a PR with a description of what changed and why

**Commit message format:**
```
type: short description (max 72 chars)

Optional longer explanation if needed.
```

Examples:
```
feat: add Playwright test result loader
fix: handle empty Confluence page body
docs: add API usage examples to README
refactor: simplify chunk overlap logic
```

---

## What we welcome

- New data source loaders (Testrail, Zephyr, GitHub Issues, Notion)
- New QA output modules (mutation testing suggestions, test data generation)
- CI/CD integration examples (GitLab, Jenkins, GitHub Actions)
- Improvements to chunking or retrieval quality
- Bug fixes and performance improvements

---

## Questions?

Open a GitHub Discussion or file an issue. We're happy to help you get started.
