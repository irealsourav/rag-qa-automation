# RAG-based Autonomous QA Framework — Design & Build Notes

Handoff document for continuing work in Claude Code.
Repo: github.com/irealsourav/rag-qa-automation
Owner: Sourav Ghosh — Senior QA Engineer, Berlin.

Write simple, clear code. Build in small pieces. Understand every part before moving on
— this project is used in interviews, so every line must be explainable.

---

## 1. The goal

Build an autonomous, self-healing QA automation framework that uses RAG
(Retrieval-Augmented Generation) to help generate tests, understand failures,
and heal broken locators.

Two different ideas power it:
- AI-assisted testing = using AI to help do the testing (generate tests, triage, heal).
- Testing non-deterministic AI = testing features whose output changes each run
  (needs evaluation, not exact-match asserts).

---

## 2. How to think about it (design order)

Questions first, then sources, then indexing. The agent needs to retrieve context to
answer questions like:
- "What should this feature do?"        -> Jira / Confluence
- "How do we usually test this?"        -> existing Cypress tests
- "What does this API return?"          -> backend contracts (OpenAPI/Swagger)
- "What elements are on this page?"     -> frontend DOM / selectors
- "Has this failed before, and why?"    -> past test results

Retrieval design flows backwards from those questions.

---

## 3. The four knowledge sources

1. Jira      — the "why": user stories, acceptance criteria, bugs.
2. Cypress   — the "how we test": existing test code, patterns, coverage.
3. Backend   — the "contract": API specs, endpoints, request/response shapes.
4. Frontend  — the "surface": DOM structure, components, selectors/data-test-ids
               (key for self-healing).

---

## 4. Design patterns (core decisions)

- SEPARATE COLLECTIONS per source in ChromaDB — do NOT mix Jira, Cypress, backend,
  frontend in one pile. Different knowledge types, different structure.
- ROUTER decides which collection(s) to query per task (this is the "agentic" part).
- METADATA on every chunk: source, feature, ticket_id, file_path, date — enables
  precise filtering, often more powerful than semantic search alone.
- PER-SOURCE CHUNKING by natural unit:
    - Jira     -> one chunk per ticket (title + description + acceptance criteria)
    - Cypress  -> one chunk per test block (describe/it), whole test intact
    - Backend  -> one chunk per endpoint (method + path + schema)
    - Frontend -> one chunk per component / page section (with selectors)

---

## 5. LangChain vs LangGraph (roles)

- LangChain = the PARTS (toolbox/glue): loaders, text splitters, embeddings wrappers,
  vector store integrations, retrievers, LLM wrappers, simple linear "chains".
  Good for linear flows: retrieve -> prompt -> generate.

- LangGraph = the BRAIN (control flow): build the agent as a graph with nodes, edges,
  branches and LOOPS. Needed because self-healing is a reason-act-check LOOP, not linear.

Self-healing loop as a graph:
  1. Run test
  2. Passed? -> yes: done. no: continue
  3. Retrieve context (R layer: current DOM, selectors, original test intent)
  4. Diagnose (LLM: why did it break?)
  5. Heal (LLM: propose new selector)
  6. Re-run -> back to step 2; after N tries, escalate to a human.

Mapping to our design:
  - 4 sources     -> loaded/embedded via LangChain into ChromaDB collections
  - router        -> a node/branch in LangGraph
  - retrieve()    -> a LangChain retriever, called inside LangGraph nodes
  - heal/retry    -> the LangGraph graph itself

---

## 6. Evals (the QA edge — measure if it's actually good)

An eval = a dataset of test cases + a way to score output. It's the regression suite
for an AI system. Evaluate each stage SEPARATELY:

1. Retrieval — did it fetch the right chunks?  Metrics: precision, recall.
2. Generation — is the generated test good?
     - runs without syntax errors (hard check)
     - tests the described behaviour (LLM-as-judge against a rubric)
     - similar in intent to a reference "gold" test (semantic similarity)
3. Healing — take deliberately broken locators with known fixes; did it heal correctly?
     Metric: healing success rate. ALSO track FALSE-HEAL rate (wrongly "fixing" a test
     that should have failed — dangerous, hides real bugs).
4. End-to-end — over many runs: % broken tests fixed autonomously; false-heal rate.

Run evals in CI so any prompt/model/retrieval change is caught as a regression.
Tools: LangSmith (tracing + evals), RAGAS (RAG metrics: faithfulness, answer relevancy,
context precision/recall), or a custom harness.

---

## 7. BUILD ORDER

### Path A — do first (small, complete, explainable)
A working Jira retrieval layer + an eval for it.

Folders to add:
    retrieval/
      build_index.py        # load + chunk + embed + store Jira tickets
      jira_retriever.py      # the R layer: retrieve(query, k)
    evals/
      eval_dataset.json      # questions + expected ticket ids
      eval_retrieval.py      # scores retrieval accuracy

Install:
    pip install langchain langchain-community chromadb sentence-transformers

Success check: ask "how is a failed login handled?" and it retrieves the wrong-password
ticket even though the words differ. That is semantic retrieval working — the real "R".

### Path B — after the interview (the full system)
Multi-source loaders (Cypress, backend, frontend) -> router -> LangGraph self-healing
loop -> full evals in CI. Built properly over weeks.

---

## 8. Honest scope notes (do not overclaim)

- Frontend/DOM retrieval for self-healing is the HARDEST piece. The DOM is huge and
  changes constantly; embedding a whole live DOM is impractical. Real self-healing is
  a HYBRID: pre-indexed known components + LIVE DOM captured at failure time, matched by
  the LLM. Not pure RAG.
- Index freshness: code/tickets change daily; need re-indexing (on commit / nightly).
- Retrieval quality itself must be tested (the two-sided problem: wrong chunks -> wrong
  output even with a perfect LLM).
- Current honest status: hand-built RAG pipeline to learn; architecture understood;
  LangChain/LangGraph/evals designed for and being built toward. Not yet a finished product.

---

## 9. Reference code — Path A

> **Status (2026-09-29): Path A is implemented** in `qa_assistant/knowledge_base/`
> (`jira_store.py`, `build_jira_index.py`, `jira_retriever.py`) and `tests/evals/`. The code below
> is the original sketch and no longer runs on current LangChain (1.x):
> - `langchain.schema` was removed; `Document` now comes from `langchain_core.documents`.
> - `langchain-community` is being sunset. Chroma and HuggingFace embeddings moved to their
>   own packages: `langchain_chroma.Chroma` and `langchain_huggingface.HuggingFaceEmbeddings`.
> - `Chroma` no longer has `persist()`; it saves to `persist_directory` automatically.
>
> The sketch's 2-ticket dataset with `k=3` would always score 100% (every query returns
> every ticket), so the real version indexes 18 sample tickets (`sample_data/jira/tickets.json`)
> and evaluates 18 reworded questions. A keyword-overlap baseline scores 50% hit@1 on the
> same questions; the embedding retriever scores 100%. Both sets were written by the same
> author, so treat this as a working pipeline, not a measurement on real data.

### retrieval/build_index.py
```python
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document

# In real use these come from the Jira API; example data here.
jira_tickets = [
    {"id": "QA-101", "title": "Login with valid credentials",
     "description": "User enters valid email and password and is redirected to dashboard."},
    {"id": "QA-102", "title": "Login with wrong password",
     "description": "User enters wrong password and sees an error message."},
]

# chunk per ticket = natural unit; keep metadata
docs = [
    Document(page_content=f"{t['title']}. {t['description']}",
             metadata={"source": "jira", "ticket_id": t["id"]})
    for t in jira_tickets
]

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
db = Chroma.from_documents(docs, embeddings,
                           collection_name="jira",
                           persist_directory="./chroma_db")
db.persist()
print(f"Indexed {len(docs)} Jira tickets.")
```

### retrieval/jira_retriever.py
```python
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

def get_jira_retriever(k=3):
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    db = Chroma(collection_name="jira",
                embedding_function=embeddings,
                persist_directory="./chroma_db")
    return db.as_retriever(search_kwargs={"k": k})

def retrieve(query, k=3):
    retriever = get_jira_retriever(k)
    results = retriever.invoke(query)
    return [(d.page_content, d.metadata["ticket_id"]) for d in results]

if __name__ == "__main__":
    for text, ticket in retrieve("how is a failed login handled?"):
        print(f"[{ticket}] {text}")
```

### evals/eval_dataset.json
```json
[
  {"query": "how is a failed login handled?", "expected_ticket": "QA-102"},
  {"query": "user logs in successfully", "expected_ticket": "QA-101"}
]
```

### evals/eval_retrieval.py
```python
import json
from retrieval.jira_retriever import retrieve

with open("evals/eval_dataset.json") as f:
    dataset = json.load(f)

hits = 0
for case in dataset:
    got = [tid for _, tid in retrieve(case["query"], k=3)]
    ok = case["expected_ticket"] in got
    hits += ok
    print(f"{'PASS' if ok else 'FAIL'}  {case['query']} -> {got}")

print(f"\nRetrieval accuracy: {hits}/{len(dataset)} = {hits/len(dataset):.0%}")
```
