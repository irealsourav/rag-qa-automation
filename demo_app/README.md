# demo_app — the website being tested

**Conduit** is a small blogging site (like a mini Medium): people sign up, write articles,
comment, favourite articles and follow each other. It exists so that the tests and the AI
assistant have a real application to work on.

| Folder | What's inside |
|---|---|
| `frontend/` | The website people see, built with Angular. Copied from the open-source [RealWorld Angular app](https://github.com/realworld-apps/angular-realworld-example-app) (MIT licence, see `frontend/LICENSE`) |
| `backend/` | The server behind it, written for this repo in Python (FastAPI + SQLite). It follows the official [RealWorld API spec](https://realworld.show) and passes its official test suite |

## Run it

```bash
pip install -r demo_app/backend/requirements.txt
python -m demo_app.backend.seed                              # load the demo data (resets everything)
python -m uvicorn demo_app.backend.main:app --port 3000      # server on :3000

cd demo_app/frontend && npm ci && npm start                  # website on http://localhost:4200
```

Demo accounts, all with the password `password123`:
`alice@conduit.test`, `bob@conduit.test`, `carol@conduit.test`.

The demo data is fixed (see `backend/seed.py`), so tests always start from the same state.

## Its tests

- Browser tests: [`tests/e2e/demo_app/`](../tests/e2e/demo_app/), see [tests/README.md](../tests/README.md)
- Server unit tests: [`tests/unit/test_demo_backend.py`](../tests/unit/test_demo_backend.py)
- The frontend's own unit tests: `cd demo_app/frontend && npx vitest run`
