import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "knowledge.db"


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                url TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)


def save_article(url, title, content, content_hash):
    with connect() as conn:
        conn.execute("""
            INSERT INTO articles (url, title, content, content_hash, active)
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT(url) DO UPDATE SET
                title = excluded.title,
                content = excluded.content,
                content_hash = excluded.content_hash,
                active = 1,
                updated_at = CURRENT_TIMESTAMP
        """, (url, title, content, content_hash))


def search_articles(query, limit=5):
    words = set(query.lower().split())
    if not words:
        return []

    with connect() as conn:
        rows = conn.execute("""
            SELECT url, title, content
            FROM articles
            WHERE active = 1
        """).fetchall()

    results = []
    for row in rows:
        text = f"{row['title']} {row['content']}".lower()
        score = sum(text.count(word) for word in words if len(word) > 2)

        if score:
            results.append({
                "url": row["url"],
                "title": row["title"],
                "content": row["content"],
                "score": score,
            })

    return sorted(
        results, key=lambda item: item["score"], reverse=True
    )[:limit]