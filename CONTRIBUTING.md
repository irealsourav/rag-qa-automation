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
flake8 . --max-line-length=100 --exclude=venv,chroma_db
```

---

## Project structure

```
rag-qa-automation/
├── ingest/          ← Data loaders (Jira, Confluence, codebase, test results)
├── pipeline/        ← Chunker, embedder, vector store
├── qa_outputs/      ← Test generator, Q&A, flaky detector, coverage analyser
├── api/             ← FastAPI REST endpoints
└── run.py           ← CLI entrypoint
```

Adding a new data source? Create a loader in `ingest/` following the same pattern as `jira_loader.py`. Each loader should return `List[Dict]` with at minimum: `id`, `source`, `content`.

Adding a new QA output? Create a module in `qa_outputs/` and expose it via both the CLI (`run.py`) and the API (`api/main.py`).

---

## Submitting a pull request

1. Make sure your branch is up to date with `main`
2. Write or update tests if relevant
3. Run linting: `flake8 . --max-line-length=100`
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
