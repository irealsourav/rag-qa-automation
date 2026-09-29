# CLAUDE.md — rag-qa-automation

Project context for Claude Code. Read this at the start of every session.

## What this is
A personal, in-progress learning project: a RAG-based, autonomous, self-healing QA
automation framework. Built by Sourav Ghosh (Senior QA Engineer) to learn AI engineering
hands-on and to support AI-QA job applications. It is NOT a finished product.

## Goal
Use RAG to help generate tests, understand failures, and heal broken locators —
pulling context from Jira, existing Cypress tests, backend API contracts, and frontend
structure.

## How I work
- Build in small pieces. Run each piece before moving on.
- I must be able to explain every line (it comes up in interviews) — so prefer clear,
  simple code over clever code, and explain what you generate.
- I use Windsurf/VS Code, clone the repo, and want targeted, file-level changes —
  not giant rewrites.
- Full design and build plan is in docs/rag-design.md — read it before implementing.

## Layout
- `rag_engine/` — the AI tool: `sources/<source>/` (one folder per source: read, chunk, index,
  retrieve) → `knowledge_base/` (shared store + embeddings) → `features/`;
  used through `cli.py`, `api.py` and `mcp_server.py` (MCP tools for AI clients)
- `demo_app/` — the app under test (Angular frontend, FastAPI backend)
- `tests/` — `unit/` (pytest), `e2e/` (Cypress), `evals/` (AI quality scores)
- `sample_data/` — example tickets, test files and reports
Each folder has a plain-English README; keep them up to date when things move.

## Stack
Python, ChromaDB, FastAPI, sentence-transformers, LangChain (parts), LangGraph (control
flow, later), evals (RAGAS / LangSmith / custom).

## Build order
1. Path A (do first): Jira retrieval layer + a retrieval eval. See docs/rag-design.md.
2. Path B (later): multi-source loaders, router, LangGraph self-healing loop, full evals in CI.

## Honesty rule
Do not add features or claims that aren't real. Mark work-in-progress clearly. If
something is hard or only partly done (e.g. live-DOM self-healing), say so in comments.
