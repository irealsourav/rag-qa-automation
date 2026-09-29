"""
Resets the Conduit database and loads fixed demo data, so UI tests always start from the same state.

    python -m demo_app.backend.seed
"""
import os

from demo_app.backend import db
from demo_app.backend.auth import hash_password

# Every demo user has the password below. Cypress logs in with these accounts.
DEMO_PASSWORD = "password123"

USERS = [
    ("alice", "alice@conduit.test", "QA lead. Writes about test strategy."),
    ("bob", "bob@conduit.test", "Frontend developer."),
    ("carol", "carol@conduit.test", None),
]

# (author, slug, title, description, body, tags)
ARTICLES = [
    ("alice", "stop-using-fixed-waits-in-cypress", "Stop using fixed waits in Cypress",
     "Why cy.wait(2000) makes tests flaky",
     "Fixed sleeps either waste time or are too short on a slow CI runner. "
     "Wait on an aliased request with `cy.intercept` and `cy.wait('@alias')` instead.",
     ["cypress", "flaky-tests", "testing"]),
    ("alice", "what-to-test-first", "What to test first",
     "Risk-based prioritisation for small QA teams",
     "Start with the flows that lose money when they break: sign-up, login and payments.",
     ["testing", "strategy"]),
    ("bob", "angular-signals-in-practice", "Angular signals in practice",
     "Replacing BehaviorSubject with signals",
     "Signals make component state easier to read. Here is how we migrated a form.",
     ["angular", "frontend"]),
    ("bob", "writing-stable-selectors", "Writing stable selectors",
     "Use data-cy attributes, not CSS classes",
     "Class names change with every redesign. A dedicated test attribute does not.",
     ["cypress", "frontend", "testing"]),
    ("carol", "hello-conduit", "Hello Conduit",
     "My first article",
     "Just trying out the editor.",
     []),
]

FAVORITES = [("bob", "stop-using-fixed-waits-in-cypress"), ("carol", "stop-using-fixed-waits-in-cypress"),
             ("alice", "writing-stable-selectors")]
FOLLOWS = [("alice", "bob"), ("carol", "alice")]
COMMENTS = [
    ("bob", "stop-using-fixed-waits-in-cypress", "This fixed half of our flaky suite."),
    ("carol", "stop-using-fixed-waits-in-cypress", "What about waiting for animations?"),
]


def seed(path: str = None):
    path = path or db.DB_PATH
    if os.path.exists(path):
        os.remove(path)
    db.init_db(path)
    conn = db.connect(path)
    password_hash = hash_password(DEMO_PASSWORD)
    user_ids = {}
    for username, email, bio in USERS:
        cur = conn.execute(
            "INSERT INTO users (username, email, password_hash, bio) VALUES (?, ?, ?, ?)",
            (username, email, password_hash, bio),
        )
        user_ids[username] = cur.lastrowid

    article_ids = {}
    # Oldest first, one minute apart, so the default "newest first" order is predictable
    for minute, (author, slug, title, description, body, tags) in enumerate(ARTICLES):
        created = f"2026-01-01T09:{minute:02d}:00.000Z"
        cur = conn.execute(
            "INSERT INTO articles (slug, title, description, body, author_id, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (slug, title, description, body, user_ids[author], created, created),
        )
        article_ids[slug] = cur.lastrowid
        conn.executemany(
            "INSERT INTO article_tags (article_id, tag, position) VALUES (?, ?, ?)",
            [(cur.lastrowid, tag, i) for i, tag in enumerate(tags)],
        )

    conn.executemany("INSERT INTO favorites (user_id, article_id) VALUES (?, ?)",
                     [(user_ids[u], article_ids[s]) for u, s in FAVORITES])
    conn.executemany("INSERT INTO follows (follower_id, followed_id) VALUES (?, ?)",
                     [(user_ids[a], user_ids[b]) for a, b in FOLLOWS])
    for minute, (author, slug, body) in enumerate(COMMENTS):
        created = f"2026-01-02T09:{minute:02d}:00.000Z"
        conn.execute(
            "INSERT INTO comments (article_id, author_id, body, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (article_ids[slug], user_ids[author], body, created, created),
        )
    conn.commit()
    conn.close()
    print(f"[seed] {len(USERS)} users, {len(ARTICLES)} articles -> {path}")


if __name__ == "__main__":
    seed()
