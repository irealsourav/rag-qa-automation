"""
Conduit API: a RealWorld-spec backend (https://realworld.show) for the demo app under test.
It backs the Angular frontend in demo_app/frontend and stores data in SQLite.
"""
import re
import secrets
import sqlite3
from contextlib import asynccontextmanager
from typing import Dict, Iterator, List, Optional

import jwt
from fastapi import Depends, FastAPI, Header, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from demo_app.backend import db
from demo_app.backend.auth import create_token, decode_token, hash_password, verify_password


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    yield


app = FastAPI(
    title="Conduit API", description="RealWorld backend for the demo app under test", lifespan=lifespan
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ApiError(Exception):
    def __init__(self, status: int, field: str, message: str):
        self.status, self.field, self.message = status, field, message


@app.exception_handler(ApiError)
def _api_error(_: Request, exc: ApiError):
    return JSONResponse(status_code=exc.status, content={"errors": {exc.field: [exc.message]}})


@app.exception_handler(RequestValidationError)
def _validation_error(_: Request, exc: RequestValidationError):
    errors: Dict[str, List[str]] = {}
    for err in exc.errors():
        errors.setdefault(str(err["loc"][-1]), []).append("is invalid")
    return JSONResponse(status_code=422, content={"errors": errors})


def get_db() -> Iterator[sqlite3.Connection]:
    conn = db.connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------- auth helpers

def _user_id_from_header(authorization: Optional[str], conn: sqlite3.Connection) -> Optional[int]:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme not in ("Token", "Bearer") or not token:
        raise ApiError(401, "token", "is invalid")
    try:
        user_id = decode_token(token)
    except jwt.InvalidTokenError:
        raise ApiError(401, "token", "is invalid")
    if not conn.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone():
        raise ApiError(401, "token", "is invalid")
    return user_id


def optional_user(
    authorization: Optional[str] = Header(None), conn: sqlite3.Connection = Depends(get_db)
) -> Optional[int]:
    return _user_id_from_header(authorization, conn)


def required_user(
    authorization: Optional[str] = Header(None), conn: sqlite3.Connection = Depends(get_db)
) -> int:
    user_id = _user_id_from_header(authorization, conn)
    if user_id is None:
        raise ApiError(401, "token", "is missing")
    return user_id


# ---------------------------------------------------------------- request helpers

async def _read_body(request: Request, key: str) -> dict:
    try:
        data = await request.json()
    except ValueError:
        raise ApiError(422, "body", "is invalid")
    if not isinstance(data, dict) or not isinstance(data.get(key), dict):
        raise ApiError(422, key, "is missing")
    return data[key]


def _blank(value) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _require(data: dict, *fields: str):
    for field in fields:
        if _blank(data.get(field)):
            raise ApiError(422, field, "can't be blank")
        if not isinstance(data[field], str):
            raise ApiError(422, field, "is invalid")


MIN_PASSWORD_LENGTH = 8


def _check_password(password: str):
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ApiError(422, "password", f"is too short (minimum is {MIN_PASSWORD_LENGTH} characters)")


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or secrets.token_hex(4)


def _unique_slug(conn: sqlite3.Connection, title: str, article_id: int = None) -> str:
    base = slug = _slugify(title)
    while True:
        row = conn.execute("SELECT id FROM articles WHERE slug = ?", (slug,)).fetchone()
        if not row or row["id"] == article_id:
            return slug
        slug = f"{base}-{secrets.token_hex(3)}"


# ---------------------------------------------------------------- serialisers

def _user_json(row: sqlite3.Row) -> dict:
    return {
        "email": row["email"],
        "token": create_token(row["id"]),
        "username": row["username"],
        "bio": row["bio"],
        "image": row["image"],
    }


def _profile_json(conn: sqlite3.Connection, user: sqlite3.Row, viewer_id: Optional[int]) -> dict:
    following = bool(viewer_id) and conn.execute(
        "SELECT 1 FROM follows WHERE follower_id = ? AND followed_id = ?", (viewer_id, user["id"])
    ).fetchone() is not None
    return {"username": user["username"], "bio": user["bio"], "image": user["image"], "following": following}


def _article_json(conn, article: sqlite3.Row, viewer_id: Optional[int], with_body: bool = True) -> dict:
    tags = [r["tag"] for r in conn.execute(
        "SELECT tag FROM article_tags WHERE article_id = ? ORDER BY position", (article["id"],)
    )]
    count = conn.execute(
        "SELECT COUNT(*) FROM favorites WHERE article_id = ?", (article["id"],)
    ).fetchone()[0]
    favorited = bool(viewer_id) and conn.execute(
        "SELECT 1 FROM favorites WHERE article_id = ? AND user_id = ?", (article["id"], viewer_id)
    ).fetchone() is not None
    author = conn.execute("SELECT * FROM users WHERE id = ?", (article["author_id"],)).fetchone()
    result = {
        "slug": article["slug"],
        "title": article["title"],
        "description": article["description"],
        "tagList": tags,
        "createdAt": article["created_at"],
        "updatedAt": article["updated_at"],
        "favorited": favorited,
        "favoritesCount": count,
        "author": _profile_json(conn, author, viewer_id),
    }
    if with_body:
        result["body"] = article["body"]
    return result


def _comment_json(conn, comment: sqlite3.Row, viewer_id: Optional[int]) -> dict:
    author = conn.execute("SELECT * FROM users WHERE id = ?", (comment["author_id"],)).fetchone()
    return {
        "id": comment["id"],
        "createdAt": comment["created_at"],
        "updatedAt": comment["updated_at"],
        "body": comment["body"],
        "author": _profile_json(conn, author, viewer_id),
    }


def _get_article(conn, slug: str) -> sqlite3.Row:
    article = conn.execute("SELECT * FROM articles WHERE slug = ?", (slug,)).fetchone()
    if not article:
        raise ApiError(404, "article", "not found")
    return article


def _get_profile_user(conn, username: str) -> sqlite3.Row:
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if not user:
        raise ApiError(404, "profile", "not found")
    return user


def _set_tags(conn, article_id: int, tags):
    if tags is None:
        return
    if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
        raise ApiError(422, "tagList", "is invalid")
    conn.execute("DELETE FROM article_tags WHERE article_id = ?", (article_id,))
    unique = list(dict.fromkeys(t.strip() for t in tags if t.strip()))
    conn.executemany(
        "INSERT INTO article_tags (article_id, tag, position) VALUES (?, ?, ?)",
        [(article_id, tag, i) for i, tag in enumerate(unique)],
    )


# ---------------------------------------------------------------- users

@app.post("/api/users/login")
async def login(request: Request, conn=Depends(get_db)):
    data = await _read_body(request, "user")
    _require(data, "email", "password")
    user = conn.execute("SELECT * FROM users WHERE email = ?", (data["email"],)).fetchone()
    if not user or not verify_password(data["password"], user["password_hash"]):
        raise ApiError(401, "credentials", "invalid")
    return {"user": _user_json(user)}


@app.post("/api/users", status_code=201)
async def register(request: Request, conn=Depends(get_db)):
    data = await _read_body(request, "user")
    _require(data, "username", "email", "password")
    _check_password(data["password"])
    for field in ("username", "email"):
        if conn.execute(f"SELECT 1 FROM users WHERE {field} = ?", (data[field],)).fetchone():
            raise ApiError(409, field, "has already been taken")
    cur = conn.execute(
        "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
        (data["username"], data["email"], hash_password(data["password"])),
    )
    user = conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
    return {"user": _user_json(user)}


@app.get("/api/user")
def current_user(user_id: int = Depends(required_user), conn=Depends(get_db)):
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return {"user": _user_json(user)}


@app.put("/api/user")
async def update_user(request: Request, user_id: int = Depends(required_user), conn=Depends(get_db)):
    data = await _read_body(request, "user")
    updates = {}
    for field in ("username", "email", "password"):
        if field in data:
            if _blank(data[field]) or not isinstance(data[field], str):
                raise ApiError(422, field, "can't be blank")
            updates[field] = data[field]
    for field in ("bio", "image"):
        if field in data:
            if data[field] is not None and not isinstance(data[field], str):
                raise ApiError(422, field, "is invalid")
            updates[field] = data[field] or None
    for field in ("username", "email"):
        if field in updates and conn.execute(
            f"SELECT 1 FROM users WHERE {field} = ? AND id != ?", (updates[field], user_id)
        ).fetchone():
            raise ApiError(409, field, "has already been taken")
    if "password" in updates:
        _check_password(updates["password"])
        updates["password_hash"] = hash_password(updates.pop("password"))
    if updates:
        assignments = ", ".join(f"{k} = ?" for k in updates)
        conn.execute(f"UPDATE users SET {assignments} WHERE id = ?", (*updates.values(), user_id))
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return {"user": _user_json(user)}


# ---------------------------------------------------------------- profiles

@app.get("/api/profiles/{username}")
def get_profile(username: str, viewer_id=Depends(optional_user), conn=Depends(get_db)):
    return {"profile": _profile_json(conn, _get_profile_user(conn, username), viewer_id)}


@app.post("/api/profiles/{username}/follow")
def follow(username: str, user_id: int = Depends(required_user), conn=Depends(get_db)):
    target = _get_profile_user(conn, username)
    conn.execute(
        "INSERT OR IGNORE INTO follows (follower_id, followed_id) VALUES (?, ?)", (user_id, target["id"])
    )
    return {"profile": _profile_json(conn, target, user_id)}


@app.delete("/api/profiles/{username}/follow")
def unfollow(username: str, user_id: int = Depends(required_user), conn=Depends(get_db)):
    target = _get_profile_user(conn, username)
    conn.execute("DELETE FROM follows WHERE follower_id = ? AND followed_id = ?", (user_id, target["id"]))
    return {"profile": _profile_json(conn, target, user_id)}


# ---------------------------------------------------------------- articles

def _list_articles(conn, viewer_id, where: List[str], params: list, limit: int, offset: int) -> dict:
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    total = conn.execute(f"SELECT COUNT(*) FROM articles a {clause}", params).fetchone()[0]
    rows = conn.execute(
        f"SELECT a.* FROM articles a {clause} ORDER BY a.created_at DESC, a.id DESC LIMIT ? OFFSET ?",
        [*params, limit, offset],
    ).fetchall()
    return {
        "articles": [_article_json(conn, r, viewer_id, with_body=False) for r in rows],
        "articlesCount": total,
    }


def _check_paging(limit: int, offset: int):
    if limit < 1:
        raise ApiError(422, "limit", "is invalid")
    if offset < 0:
        raise ApiError(422, "offset", "is invalid")


@app.get("/api/articles/feed")
def feed(limit: int = 20, offset: int = 0, user_id: int = Depends(required_user), conn=Depends(get_db)):
    _check_paging(limit, offset)
    where = ["a.author_id IN (SELECT followed_id FROM follows WHERE follower_id = ?)"]
    return _list_articles(conn, user_id, where, [user_id], limit, offset)


@app.get("/api/articles")
def list_articles(
    tag: Optional[str] = None,
    author: Optional[str] = None,
    favorited: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    viewer_id=Depends(optional_user),
    conn=Depends(get_db),
):
    _check_paging(limit, offset)
    where, params = [], []
    if tag:
        where.append("EXISTS (SELECT 1 FROM article_tags t WHERE t.article_id = a.id AND t.tag = ?)")
        params.append(tag)
    if author:
        where.append("a.author_id = (SELECT id FROM users WHERE username = ?)")
        params.append(author)
    if favorited:
        where.append(
            "EXISTS (SELECT 1 FROM favorites f JOIN users u ON u.id = f.user_id"
            " WHERE f.article_id = a.id AND u.username = ?)"
        )
        params.append(favorited)
    return _list_articles(conn, viewer_id, where, params, limit, offset)


@app.post("/api/articles", status_code=201)
async def create_article(request: Request, user_id: int = Depends(required_user), conn=Depends(get_db)):
    data = await _read_body(request, "article")
    _require(data, "title", "description", "body")
    now = db.now_iso()
    cur = conn.execute(
        "INSERT INTO articles (slug, title, description, body, author_id, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (_unique_slug(conn, data["title"]), data["title"], data["description"], data["body"],
         user_id, now, now),
    )
    _set_tags(conn, cur.lastrowid, data.get("tagList") or [])
    article = conn.execute("SELECT * FROM articles WHERE id = ?", (cur.lastrowid,)).fetchone()
    return {"article": _article_json(conn, article, user_id)}


@app.get("/api/articles/{slug}")
def get_article(slug: str, viewer_id=Depends(optional_user), conn=Depends(get_db)):
    return {"article": _article_json(conn, _get_article(conn, slug), viewer_id)}


@app.put("/api/articles/{slug}")
async def update_article(
    slug: str, request: Request, user_id: int = Depends(required_user), conn=Depends(get_db)
):
    article = _get_article(conn, slug)
    if article["author_id"] != user_id:
        raise ApiError(403, "article", "forbidden")
    data = await _read_body(request, "article")
    updates = {}
    for field in ("title", "description", "body"):
        if field in data:
            if _blank(data[field]) or not isinstance(data[field], str):
                raise ApiError(422, field, "can't be blank")
            updates[field] = data[field]
    if "title" in updates:
        updates["slug"] = _unique_slug(conn, updates["title"], article["id"])
    if "tagList" in data and data["tagList"] is None:
        raise ApiError(422, "tagList", "is invalid")
    updates["updated_at"] = db.now_iso()
    assignments = ", ".join(f"{k} = ?" for k in updates)
    conn.execute(f"UPDATE articles SET {assignments} WHERE id = ?", (*updates.values(), article["id"]))
    _set_tags(conn, article["id"], data.get("tagList"))
    article = conn.execute("SELECT * FROM articles WHERE id = ?", (article["id"],)).fetchone()
    return {"article": _article_json(conn, article, user_id)}


@app.delete("/api/articles/{slug}", status_code=204)
def delete_article(slug: str, user_id: int = Depends(required_user), conn=Depends(get_db)):
    article = _get_article(conn, slug)
    if article["author_id"] != user_id:
        raise ApiError(403, "article", "forbidden")
    conn.execute("DELETE FROM articles WHERE id = ?", (article["id"],))
    return Response(status_code=204)


# ---------------------------------------------------------------- favorites

@app.post("/api/articles/{slug}/favorite")
def favorite(slug: str, user_id: int = Depends(required_user), conn=Depends(get_db)):
    article = _get_article(conn, slug)
    conn.execute("INSERT OR IGNORE INTO favorites (user_id, article_id) VALUES (?, ?)", (user_id, article["id"]))
    return {"article": _article_json(conn, article, user_id)}


@app.delete("/api/articles/{slug}/favorite")
def unfavorite(slug: str, user_id: int = Depends(required_user), conn=Depends(get_db)):
    article = _get_article(conn, slug)
    conn.execute("DELETE FROM favorites WHERE user_id = ? AND article_id = ?", (user_id, article["id"]))
    return {"article": _article_json(conn, article, user_id)}


# ---------------------------------------------------------------- comments

@app.get("/api/articles/{slug}/comments")
def list_comments(slug: str, viewer_id=Depends(optional_user), conn=Depends(get_db)):
    article = _get_article(conn, slug)
    rows = conn.execute(
        "SELECT * FROM comments WHERE article_id = ? ORDER BY created_at DESC, id DESC", (article["id"],)
    ).fetchall()
    return {"comments": [_comment_json(conn, r, viewer_id) for r in rows]}


@app.post("/api/articles/{slug}/comments", status_code=201)
async def add_comment(
    slug: str, request: Request, user_id: int = Depends(required_user), conn=Depends(get_db)
):
    article = _get_article(conn, slug)
    data = await _read_body(request, "comment")
    _require(data, "body")
    now = db.now_iso()
    cur = conn.execute(
        "INSERT INTO comments (article_id, author_id, body, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (article["id"], user_id, data["body"], now, now),
    )
    comment = conn.execute("SELECT * FROM comments WHERE id = ?", (cur.lastrowid,)).fetchone()
    return {"comment": _comment_json(conn, comment, user_id)}


@app.delete("/api/articles/{slug}/comments/{comment_id}", status_code=204)
def delete_comment(slug: str, comment_id: int, user_id: int = Depends(required_user), conn=Depends(get_db)):
    article = _get_article(conn, slug)
    comment = conn.execute(
        "SELECT * FROM comments WHERE id = ? AND article_id = ?", (comment_id, article["id"])
    ).fetchone()
    if not comment:
        raise ApiError(404, "comment", "not found")
    if comment["author_id"] != user_id:
        raise ApiError(403, "comment", "forbidden")
    conn.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
    return Response(status_code=204)


# ---------------------------------------------------------------- tags

@app.get("/api/tags")
def tags(conn=Depends(get_db)):
    rows = conn.execute(
        "SELECT tag FROM article_tags GROUP BY tag ORDER BY COUNT(*) DESC, tag"
    ).fetchall()
    return {"tags": [r["tag"] for r in rows]}
