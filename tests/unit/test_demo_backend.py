import pytest
from fastapi.testclient import TestClient

from demo_app.backend import db
from demo_app.backend.main import app
from demo_app.backend.seed import DEMO_PASSWORD, seed


@pytest.fixture
def client(tmp_path, monkeypatch):
    path = str(tmp_path / "conduit.db")
    monkeypatch.setattr(db, "DB_PATH", path)
    seed(path)
    with TestClient(app) as c:
        yield c


def login(client, email="alice@conduit.test"):
    res = client.post("/api/users/login", json={"user": {"email": email, "password": DEMO_PASSWORD}})
    assert res.status_code == 200
    return {"Authorization": f"Token {res.json()['user']['token']}"}


class TestAuth:
    def test_login_with_seeded_user(self, client):
        res = client.post("/api/users/login", json={"user": {"email": "alice@conduit.test", "password": DEMO_PASSWORD}})
        assert res.status_code == 200
        assert res.json()["user"]["username"] == "alice"

    def test_wrong_password_is_rejected(self, client):
        res = client.post("/api/users/login", json={"user": {"email": "alice@conduit.test", "password": "nope-nope"}})
        assert res.status_code == 401
        assert res.json() == {"errors": {"credentials": ["invalid"]}}

    def test_register_blank_username(self, client):
        res = client.post("/api/users", json={"user": {"username": "", "email": "x@y.z", "password": "password123"}})
        assert res.status_code == 422
        assert res.json()["errors"]["username"] == ["can't be blank"]

    def test_register_short_password(self, client):
        res = client.post("/api/users", json={"user": {"username": "dan", "email": "d@y.z", "password": "short"}})
        assert res.status_code == 422
        assert "password" in res.json()["errors"]

    def test_register_duplicate_email(self, client):
        res = client.post("/api/users", json={"user": {"username": "new", "email": "bob@conduit.test", "password": "password123"}})
        assert res.status_code == 409

    def test_protected_endpoint_needs_token(self, client):
        res = client.get("/api/user")
        assert res.status_code == 401
        assert res.json() == {"errors": {"token": ["is missing"]}}


class TestArticles:
    def test_list_is_newest_first_without_body(self, client):
        articles = client.get("/api/articles").json()["articles"]
        assert articles[0]["slug"] == "hello-conduit"
        assert "body" not in articles[0]

    def test_filter_by_tag(self, client):
        res = client.get("/api/articles", params={"tag": "cypress"}).json()
        assert res["articlesCount"] == 2

    def test_feed_shows_followed_authors_only(self, client):
        res = client.get("/api/articles/feed", headers=login(client)).json()
        assert {a["author"]["username"] for a in res["articles"]} == {"bob"}

    def test_create_article_makes_slug(self, client):
        res = client.post("/api/articles", headers=login(client), json={
            "article": {"title": "My New Post!", "description": "d", "body": "b", "tagList": ["qa"]}
        })
        assert res.status_code == 201
        assert res.json()["article"]["slug"] == "my-new-post"

    def test_only_author_can_edit(self, client):
        res = client.put("/api/articles/angular-signals-in-practice", headers=login(client),
                         json={"article": {"title": "Hijacked"}})
        assert res.status_code == 403

    def test_favorite_updates_count(self, client):
        slug = "what-to-test-first"
        res = client.post(f"/api/articles/{slug}/favorite", headers=login(client, "bob@conduit.test"))
        assert res.json()["article"]["favorited"] is True
        assert res.json()["article"]["favoritesCount"] == 1

    def test_popular_tags_first(self, client):
        assert client.get("/api/tags").json()["tags"][0] == "testing"


class TestComments:
    def test_cannot_delete_someone_elses_comment(self, client):
        slug = "stop-using-fixed-waits-in-cypress"
        comment_id = client.get(f"/api/articles/{slug}/comments").json()["comments"][0]["id"]
        res = client.delete(f"/api/articles/{slug}/comments/{comment_id}", headers=login(client))
        assert res.status_code == 403
