# RAG QA Automation

An AI assistant for software testers. It reads what a team already has (Jira tickets,
existing tests and past test results) and uses that knowledge to help with testing work:
writing test cases, answering questions about the tests, and explaining why tests fail.

It is a **learning project and a work in progress**. See [Project status](#project-status)
for what works today and what is still planned.

## How it works, in one picture

```
  Jira, test code,           Stored as searchable          Claude (the AI) answers
  test reports         →     "knowledge" (RAG)       →     using that knowledge
                                                                   ↓
                                           test cases, answers, flaky-test fixes
```

**RAG** (Retrieval-Augmented Generation) means: before asking the AI anything, first look
up the most relevant pieces of your own documents, and give those to the AI. The answers
are then based on your project, not just on what the AI generally knows.

## What's in this repository

| Folder | In plain words | Details |
|---|---|---|
| [`qa_assistant/`](qa_assistant/) | **The AI tool itself.** Reads your sources, stores the knowledge, and offers the features below. | [README](qa_assistant/README.md) |
| [`demo_app/`](demo_app/) | **A small example website to test**: a blogging app called Conduit. It gives the tool and the tests something real to work on. | [README](demo_app/README.md) |
| [`tests/`](tests/) | **Everything that checks quality**: quick code checks, browser tests of the demo website, and scores for how good the AI's answers are. | [README](tests/README.md) |
| [`sample_data/`](sample_data/) | **Example inputs**: made-up Jira tickets, test files and test reports, so everything can be tried without real company data. | [README](sample_data/README.md) |
| [`docs/`](docs/) | **Design notes**: the plan for where this project is going. | [rag-design.md](docs/rag-design.md) |

Files at the top level are setup files: `requirements*.txt` (Python packages),
`package.json` (JavaScript packages for Cypress), `.env.example` (settings template),
`.github/workflows/` (automatic checks on GitHub).

## What the assistant can do

| Feature | What it does |
|---|---|
| Generate test cases | Writes test cases for a feature, based on the tickets and existing tests |
| Answer questions | "Where are the login tests?", answered from the actual test code |
| Find flaky tests | Spots tests that sometimes pass and sometimes fail, and suggests why |
| Find coverage gaps | Compares requirements with tests to show what is not tested |
| Push tests to Jira | Creates the generated test cases as Jira issues linked to the story |

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env                     # then add your ANTHROPIC_API_KEY

# Load the example data, then ask a question
python -m qa_assistant ingest codebase --codebase-path sample_data/cypress_tests
python -m qa_assistant ask "which checkout tests use fixed waits?"
```

More commands are in [qa_assistant/README.md](qa_assistant/README.md).

## Project status

| Part | Status |
|---|---|
| Features above (generate, ask, flaky, coverage, Jira push) | Working |
| Jira retrieval layer + retrieval eval ("Path A" in the design notes) | Working, measured on sample data only |
| Demo app + its browser tests | Working |
| Knowledge from backend API specs and frontend pages | Not built yet |
| Self-healing tests (fixing broken selectors automatically) | Not built yet, planned with LangGraph |
| Scoring the quality of generated tests and fixes | Not built yet |

## Automatic checks on GitHub

| Workflow | When | What it checks |
|---|---|---|
| `CI` | every push and pull request to `main` | Code style, unit tests, the retrieval score, and the demo app (its own tests, its API against the official spec, and the Cypress browser tests). Free: no AI calls |
| `RAG E2E` | only when started by hand | Runs the whole assistant with real AI calls and shows the answers on the run's Summary page. Needs the `ANTHROPIC_API_KEY` secret and costs API credits |

## Tech stack

Python, Claude (Anthropic), ChromaDB, sentence-transformers, LangChain, FastAPI, Typer,
Angular (demo app), Cypress.
