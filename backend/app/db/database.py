import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.getenv(
    "DB_PATH",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "otinish.db"))
)

def get_connection():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS appeals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            language TEXT,
            overall_confidence REAL,
            needs_human_review INTEGER,
            issue_count INTEGER,
            used_mock INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            appeal_id INTEGER REFERENCES appeals(id),
            issue_number INTEGER,
            category TEXT,
            confidence REAL,
            needs_clarification INTEGER,
            status TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()

def save_analysis(text: str, result):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO appeals (text, language, overall_confidence, needs_human_review, issue_count, used_mock, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (text[:500], result.language, result.overall_confidence,
          int(result.needs_human_review), len(result.issues), int(result.used_mock),
          datetime.utcnow().isoformat()))
    appeal_id = cursor.lastrowid
    for issue in result.issues:
        cursor.execute("""
            INSERT INTO issues (appeal_id, issue_number, category, confidence, needs_clarification, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (appeal_id, issue.issue_number, issue.category,
              issue.confidence, int(issue.needs_clarification), issue.status))
    conn.commit()
    conn.close()

def get_dashboard_stats() -> dict:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as cnt FROM appeals")
    count = cursor.fetchone()["cnt"]
    if count == 0:
        _seed_demo_stats(cursor, conn)
        cursor.execute("SELECT COUNT(*) as cnt FROM appeals")
        count = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM appeals WHERE overall_confidence >= 0.9")
    high = cursor.fetchone()["cnt"]
    cursor.execute("SELECT COUNT(*) as cnt FROM appeals WHERE overall_confidence >= 0.7 AND overall_confidence < 0.9")
    medium = cursor.fetchone()["cnt"]
    cursor.execute("SELECT COUNT(*) as cnt FROM appeals WHERE overall_confidence < 0.7")
    low = cursor.fetchone()["cnt"]
    cursor.execute("SELECT COUNT(*) as cnt FROM appeals WHERE issue_count > 1")
    multi = cursor.fetchone()["cnt"]

    cursor.execute("SELECT language, COUNT(*) as cnt FROM appeals GROUP BY language")
    lang_dist = {row["language"]: row["cnt"] for row in cursor.fetchall()}

    cursor.execute("SELECT category, COUNT(*) as cnt FROM issues GROUP BY category ORDER BY cnt DESC LIMIT 8")
    cat_dist = {row["category"]: row["cnt"] for row in cursor.fetchall()}

    conn.close()
    return {
        "total_analyzed": count,
        "high_confidence": high,
        "medium_confidence": medium,
        "needs_clarification": low,
        "multi_intent": multi,
        "language_distribution": lang_dist,
        "category_distribution": cat_dist,
        "disclaimer": "Demo analytics — not official government data"
    }

def _seed_demo_stats(cursor, conn):
    """Seed realistic demo analytics data."""
    import random
    random.seed(42)
    categories = ["land", "social", "housing", "health", "education", "roads", "utilities", "employment", "documents", "tax", "other"]
    langs = ["kk", "ru", "mixed"]

    for i in range(150):
        lang = random.choices(langs, weights=[45, 50, 5])[0]
        conf = random.uniform(0.55, 0.98)
        issue_count = random.choices([1, 2, 3], weights=[60, 30, 10])[0]
        cursor.execute("""
            INSERT INTO appeals (text, language, overall_confidence, needs_human_review, issue_count, used_mock, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (f"Demo appeal {i+1}", lang, round(conf, 2), int(conf < 0.70), issue_count, 1,
              f"2026-0{random.randint(1,9):01d}-{random.randint(1,28):02d}T10:00:00"))
        aid = cursor.lastrowid
        for j in range(issue_count):
            cat = random.choice(categories)
            cursor.execute("""
                INSERT INTO issues (appeal_id, issue_number, category, confidence, needs_clarification, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (aid, j+1, cat, round(conf, 2), int(conf < 0.70), "routed" if conf >= 0.70 else "needs_clarification"))
    conn.commit()