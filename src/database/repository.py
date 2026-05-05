from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import os
import re
import sqlite3
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from passlib.context import CryptContext

from src.database.connection import DatabaseConnection


@dataclass(frozen=True)
class ChatSession:
    id: int
    title: str
    started_at: str
    is_pinned: bool
    rag_scope: str = "all"


@dataclass(frozen=True)
class ChatMessage:
    id: int
    role: str
    content: str
    created_at: str


@dataclass(frozen=True)
class SavedPrompt:
    id: int
    title: str
    prompt_text: str
    created_at: str


@dataclass(frozen=True)
class MessageBookmark:
    id: int
    message_id: int
    note: Optional[str]
    content_preview: str
    session_title: str
    created_at: str


@dataclass(frozen=True)
class ChatSearchResult:
    session_id: int
    session_title: str
    snippet: str
    created_at: str


class ChatRepository:
    def __init__(self, database: DatabaseConnection) -> None:
        self.database = database
        self.password_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
        self._ensure_schema_migrations()

    @staticmethod
    def _add_column_if_missing(conn, table: str, column: str, declaration: str) -> None:
        cols = conn.execute(f"PRAGMA table_info({table});").fetchall()
        if any(str(c["name"]) == column for c in cols):
            return
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {declaration};")

    def _ensure_schema_migrations(self) -> None:
        with self.database.get_connection() as conn:
            columns = conn.execute("PRAGMA table_info(chat_sessions);").fetchall()
            has_is_pinned = any(str(col["name"]) == "is_pinned" for col in columns)
            if not has_is_pinned:
                conn.execute(
                    "ALTER TABLE chat_sessions ADD COLUMN is_pinned INTEGER NOT NULL DEFAULT 0;"
                )

            self._add_column_if_missing(conn, "users", "role", "role TEXT NOT NULL DEFAULT 'user'")
            self._add_column_if_missing(conn, "users", "nim", "nim TEXT")
            self._add_column_if_missing(conn, "users", "cohort", "cohort TEXT")
            self._add_column_if_missing(conn, "users", "interests", "interests TEXT")
            self._add_column_if_missing(
                conn,
                "users",
                "weekly_message_goal",
                "weekly_message_goal INTEGER NOT NULL DEFAULT 12",
            )
            self._add_column_if_missing(
                conn,
                "chat_sessions",
                "rag_scope",
                "rag_scope TEXT NOT NULL DEFAULT 'all'",
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS saved_prompts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    prompt_text TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS message_bookmarks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    note TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (message_id) REFERENCES chat_messages(id) ON DELETE CASCADE,
                    UNIQUE(user_id, message_id)
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_saved_prompts_user_id ON saved_prompts(user_id);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_message_bookmarks_user_id ON message_bookmarks(user_id);"
            )

        self._sync_admin_roles_from_env()

    def _sync_admin_roles_from_env(self) -> None:
        raw = os.getenv("ADMIN_USERNAMES", "").strip()
        if not raw:
            return
        names = [n.strip() for n in raw.split(",") if n.strip()]
        if not names:
            return
        placeholders = ",".join("?" for _ in names)
        with self.database.get_connection() as conn:
            conn.execute(
                f"UPDATE users SET role = 'admin' WHERE username IN ({placeholders});",
                names,
            )

    def ensure_default_user(self, username: str = "guest") -> int:
        with self.database.get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM users WHERE username = ?;",
                (username,),
            ).fetchone()
            if row:
                return int(row["id"])

            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?);",
                (username, "no-auth"),
            )
            created = conn.execute(
                "SELECT id FROM users WHERE username = ?;",
                (username,),
            ).fetchone()
            return int(created["id"])

    def get_user_by_username(self, username: str) -> Optional[dict]:
        with self.database.get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, username, password_hash, role, nim, cohort, interests, weekly_message_goal
                FROM users WHERE username = ?;
                """,
                (username,),
            ).fetchone()
            return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        with self.database.get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, username, password_hash, role, nim, cohort, interests, weekly_message_goal
                FROM users WHERE id = ?;
                """,
                (user_id,),
            ).fetchone()
            return dict(row) if row else None

    def is_admin(self, user_id: int) -> bool:
        user = self.get_user_by_id(user_id)
        return bool(user and str(user.get("role", "user")) == "admin")

    def update_user_profile(
        self,
        user_id: int,
        *,
        nim: str,
        cohort: str,
        interests: str,
        weekly_message_goal: int,
    ) -> None:
        goal = max(1, min(999, int(weekly_message_goal)))
        with self.database.get_connection() as conn:
            conn.execute(
                """
                UPDATE users
                SET nim = ?, cohort = ?, interests = ?, weekly_message_goal = ?
                WHERE id = ?;
                """,
                (nim.strip() or None, cohort.strip() or None, interests.strip() or None, goal, user_id),
            )

    def update_weekly_message_goal(self, user_id: int, goal: int) -> None:
        g = max(1, min(999, int(goal)))
        with self.database.get_connection() as conn:
            conn.execute(
                "UPDATE users SET weekly_message_goal = ? WHERE id = ?;",
                (g, user_id),
            )

    def admin_list_users(self) -> List[dict]:
        with self.database.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT u.id, u.username, u.role, u.created_at,
                       (SELECT COUNT(*) FROM chat_sessions s WHERE s.user_id = u.id) AS session_count,
                       (SELECT COUNT(*) FROM chat_messages m
                        JOIN chat_sessions s ON s.id = m.session_id WHERE s.user_id = u.id) AS message_count
                FROM users u
                ORDER BY u.id ASC;
                """
            ).fetchall()
            return [dict(r) for r in rows]

    def admin_set_password(self, target_user_id: int, new_password: str) -> bool:
        if len(new_password) < 6:
            return False
        h = self.password_context.hash(new_password)
        with self.database.get_connection() as conn:
            cur = conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?;",
                (h, target_user_id),
            )
            return cur.rowcount > 0

    def admin_set_role(self, target_user_id: int, role: str) -> bool:
        if role not in ("user", "admin"):
            return False
        with self.database.get_connection() as conn:
            cur = conn.execute(
                "UPDATE users SET role = ? WHERE id = ?;",
                (role, target_user_id),
            )
            return cur.rowcount > 0

    def admin_global_stats(self) -> dict:
        with self.database.get_connection() as conn:
            users = conn.execute("SELECT COUNT(*) AS c FROM users;").fetchone()
            msgs = conn.execute("SELECT COUNT(*) AS c FROM chat_messages;").fetchone()
            sess = conn.execute("SELECT COUNT(*) AS c FROM chat_sessions;").fetchone()
            return {
                "users": int(users["c"]) if users else 0,
                "messages": int(msgs["c"]) if msgs else 0,
                "sessions": int(sess["c"]) if sess else 0,
            }

    def register_user(self, username: str, password: str) -> Optional[int]:
        normalized = username.strip()
        if len(normalized) < 3 or len(password) < 6:
            return None

        existing = self.get_user_by_username(normalized)
        if existing:
            return None

        password_hash = self.password_context.hash(password)
        with self.database.get_connection() as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?);",
                (normalized, password_hash),
            )
            row = conn.execute(
                "SELECT id FROM users WHERE username = ?;",
                (normalized,),
            ).fetchone()
            return int(row["id"]) if row else None

    def authenticate_user(self, username: str, password: str) -> Optional[int]:
        user = self.get_user_by_username(username.strip())
        if not user:
            return None

        if not self.password_context.verify(password, str(user["password_hash"])):
            return None
        return int(user["id"])

    def list_sessions(self, user_id: int) -> List[ChatSession]:
        with self.database.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, COALESCE(title, 'Sesi Baru') AS title, started_at, is_pinned,
                       COALESCE(rag_scope, 'all') AS rag_scope
                FROM chat_sessions
                WHERE user_id = ?
                ORDER BY is_pinned DESC, started_at DESC, id DESC;
                """,
                (user_id,),
            ).fetchall()

            return [
                ChatSession(
                    id=int(row["id"]),
                    title=str(row["title"]),
                    started_at=str(row["started_at"]),
                    is_pinned=bool(int(row["is_pinned"]) == 1),
                    rag_scope=str(row["rag_scope"] or "all"),
                )
                for row in rows
            ]

    def get_session_rag_scope(self, user_id: int, session_id: int) -> str:
        with self.database.get_connection() as conn:
            row = conn.execute(
                """
                SELECT COALESCE(rag_scope, 'all') AS rag_scope
                FROM chat_sessions WHERE id = ? AND user_id = ?;
                """,
                (session_id, user_id),
            ).fetchone()
            return str(row["rag_scope"]) if row else "all"

    def set_session_rag_scope(self, user_id: int, session_id: int, rag_scope: str) -> bool:
        if rag_scope not in ("all", "sttnf"):
            return False
        with self.database.get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM chat_sessions WHERE id = ? AND user_id = ?;",
                (session_id, user_id),
            ).fetchone()
            if not row:
                return False
            conn.execute(
                "UPDATE chat_sessions SET rag_scope = ? WHERE id = ?;",
                (rag_scope, session_id),
            )
            return True

    def is_session_pinned(self, user_id: int, session_id: int) -> bool:
        with self.database.get_connection() as conn:
            row = conn.execute(
                """
                SELECT is_pinned
                FROM chat_sessions
                WHERE id = ? AND user_id = ?;
                """,
                (session_id, user_id),
            ).fetchone()
            return bool(row and int(row["is_pinned"]) == 1)

    def set_session_pinned(self, user_id: int, session_id: int, is_pinned: bool) -> bool:
        with self.database.get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM chat_sessions WHERE id = ? AND user_id = ?;",
                (session_id, user_id),
            ).fetchone()
            if not row:
                return False

            conn.execute(
                "UPDATE chat_sessions SET is_pinned = ? WHERE id = ?;",
                (1 if is_pinned else 0, session_id),
            )
            return True

    def create_session(self, user_id: int, title: str = "Sesi Baru") -> int:
        with self.database.get_connection() as conn:
            conn.execute(
                "INSERT INTO chat_sessions (user_id, title) VALUES (?, ?);",
                (user_id, title),
            )
            row = conn.execute("SELECT last_insert_rowid() AS id;").fetchone()
            return int(row["id"])

    def rename_session_if_default(self, session_id: int, user_prompt: str) -> None:
        title = user_prompt.strip().replace("\n", " ")
        if not title:
            return

        title = title[:48]
        with self.database.get_connection() as conn:
            row = conn.execute(
                "SELECT title FROM chat_sessions WHERE id = ?;",
                (session_id,),
            ).fetchone()
            if not row:
                return
            if str(row["title"]).strip().lower() != "sesi baru":
                return

            conn.execute(
                "UPDATE chat_sessions SET title = ? WHERE id = ?;",
                (title, session_id),
            )

    def rename_session(self, user_id: int, session_id: int, new_title: str) -> bool:
        title = new_title.strip()
        if not title:
            return False
        title = title[:64]

        with self.database.get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM chat_sessions WHERE id = ? AND user_id = ?;",
                (session_id, user_id),
            ).fetchone()
            if not row:
                return False

            conn.execute(
                "UPDATE chat_sessions SET title = ? WHERE id = ?;",
                (title, session_id),
            )
            return True

    def delete_session(self, user_id: int, session_id: int) -> bool:
        with self.database.get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM chat_sessions WHERE id = ? AND user_id = ?;",
                (session_id, user_id),
            ).fetchone()
            if not row:
                return False

            conn.execute(
                "DELETE FROM chat_sessions WHERE id = ?;",
                (session_id,),
            )
            return True

    def list_messages(self, session_id: int) -> List[ChatMessage]:
        with self.database.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, role, content, created_at
                FROM chat_messages
                WHERE session_id = ?
                ORDER BY id ASC;
                """,
                (session_id,),
            ).fetchall()
            return [
                ChatMessage(
                    id=int(row["id"]),
                    role=str(row["role"]),
                    content=str(row["content"]),
                    created_at=str(row["created_at"]),
                )
                for row in rows
            ]

    def verify_message_owned_by_user(self, user_id: int, message_id: int) -> bool:
        with self.database.get_connection() as conn:
            row = conn.execute(
                """
                SELECT 1 FROM chat_messages m
                JOIN chat_sessions s ON s.id = m.session_id
                WHERE m.id = ? AND s.user_id = ?;
                """,
                (message_id, user_id),
            ).fetchone()
            return row is not None

    def add_message_bookmark(self, user_id: int, message_id: int, note: str = "") -> bool:
        if not self.verify_message_owned_by_user(user_id, message_id):
            return False
        note_val = note.strip() or None
        try:
            with self.database.get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO message_bookmarks (user_id, message_id, note)
                    VALUES (?, ?, ?);
                    """,
                    (user_id, message_id, note_val),
                )
            return True
        except sqlite3.IntegrityError:
            return False

    def remove_message_bookmark(self, user_id: int, bookmark_id: int) -> bool:
        with self.database.get_connection() as conn:
            cur = conn.execute(
                "DELETE FROM message_bookmarks WHERE id = ? AND user_id = ?;",
                (bookmark_id, user_id),
            )
            return cur.rowcount > 0

    def list_message_bookmarks(self, user_id: int) -> List[MessageBookmark]:
        with self.database.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT b.id, b.message_id, b.note, b.created_at,
                       SUBSTR(m.content, 1, 160) AS preview,
                       COALESCE(s.title, 'Sesi Baru') AS session_title
                FROM message_bookmarks b
                JOIN chat_messages m ON m.id = b.message_id
                JOIN chat_sessions s ON s.id = m.session_id
                WHERE b.user_id = ?
                ORDER BY b.created_at DESC;
                """,
                (user_id,),
            ).fetchall()
            return [
                MessageBookmark(
                    id=int(r["id"]),
                    message_id=int(r["message_id"]),
                    note=str(r["note"]) if r["note"] else None,
                    content_preview=str(r["preview"] or ""),
                    session_title=str(r["session_title"]),
                    created_at=str(r["created_at"]),
                )
                for r in rows
            ]

    def add_saved_prompt(self, user_id: int, title: str, prompt_text: str) -> Optional[int]:
        title = title.strip()
        body = prompt_text.strip()
        if len(title) < 2 or len(body) < 4:
            return None
        title = title[:80]
        with self.database.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO saved_prompts (user_id, title, prompt_text)
                VALUES (?, ?, ?);
                """,
                (user_id, title, body[:8000]),
            )
            row = conn.execute("SELECT last_insert_rowid() AS id;").fetchone()
            return int(row["id"]) if row else None

    def delete_saved_prompt(self, user_id: int, prompt_id: int) -> bool:
        with self.database.get_connection() as conn:
            cur = conn.execute(
                "DELETE FROM saved_prompts WHERE id = ? AND user_id = ?;",
                (prompt_id, user_id),
            )
            return cur.rowcount > 0

    def list_saved_prompts(self, user_id: int) -> List[SavedPrompt]:
        with self.database.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, title, prompt_text, created_at
                FROM saved_prompts
                WHERE user_id = ?
                ORDER BY created_at DESC;
                """,
                (user_id,),
            ).fetchall()
            return [
                SavedPrompt(
                    id=int(r["id"]),
                    title=str(r["title"]),
                    prompt_text=str(r["prompt_text"]),
                    created_at=str(r["created_at"]),
                )
                for r in rows
            ]

    def days_since_last_message(self, user_id: int) -> Optional[float]:
        with self.database.get_connection() as conn:
            row = conn.execute(
                """
                SELECT MAX(m.created_at) AS last_at
                FROM chat_messages m
                JOIN chat_sessions s ON s.id = m.session_id
                WHERE s.user_id = ?;
                """,
                (user_id,),
            ).fetchone()
        if not row or not row["last_at"]:
            return None
        raw = str(row["last_at"])
        try:
            if "T" in raw:
                dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            else:
                dt = datetime.strptime(raw[:19], "%Y-%m-%d %H:%M:%S")
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            return (now - dt).total_seconds() / 86400.0
        except Exception:
            return None

    def save_message(self, session_id: int, role: str, content: str) -> int:
        with self.database.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO chat_messages (session_id, role, content)
                VALUES (?, ?, ?);
                """,
                (session_id, role, content),
            )
            row = conn.execute("SELECT last_insert_rowid() AS id;").fetchone()
            return int(row["id"]) if row else 0

    def session_exists(self, user_id: int, session_id: int) -> bool:
        with self.database.get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM chat_sessions WHERE id = ? AND user_id = ?;",
                (session_id, user_id),
            ).fetchone()
            return row is not None

    def get_latest_session_id(self, user_id: int) -> Optional[int]:
        with self.database.get_connection() as conn:
            row = conn.execute(
                """
                SELECT id
                FROM chat_sessions
                WHERE user_id = ?
                ORDER BY started_at DESC, id DESC
                LIMIT 1;
                """,
                (user_id,),
            ).fetchone()
            return int(row["id"]) if row else None

    def search_messages(self, user_id: int, query: str, limit: int = 30) -> List[ChatSearchResult]:
        keyword = query.strip()
        if not keyword:
            return []

        like_query = f"%{keyword}%"
        with self.database.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    m.session_id AS session_id,
                    COALESCE(s.title, 'Sesi Baru') AS session_title,
                    m.content AS snippet,
                    m.created_at AS created_at
                FROM chat_messages m
                JOIN chat_sessions s ON s.id = m.session_id
                WHERE s.user_id = ?
                  AND m.content LIKE ?
                ORDER BY m.created_at DESC, m.id DESC
                LIMIT ?;
                """,
                (user_id, like_query, limit),
            ).fetchall()

            return [
                ChatSearchResult(
                    session_id=int(row["session_id"]),
                    session_title=str(row["session_title"]),
                    snippet=str(row["snippet"])[:120],
                    created_at=str(row["created_at"]),
                )
                for row in rows
            ]

    def count_sessions(self, user_id: int) -> int:
        with self.database.get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS total FROM chat_sessions WHERE user_id = ?;",
                (user_id,),
            ).fetchone()
            return int(row["total"]) if row else 0

    def count_messages(self, user_id: int) -> int:
        with self.database.get_connection() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS total
                FROM chat_messages m
                JOIN chat_sessions s ON s.id = m.session_id
                WHERE s.user_id = ?;
                """,
                (user_id,),
            ).fetchone()
            return int(row["total"]) if row else 0

    def daily_message_activity(self, user_id: int, days: int = 14) -> List[tuple[str, int]]:
        with self.database.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT DATE(m.created_at) AS day, COUNT(*) AS total
                FROM chat_messages m
                JOIN chat_sessions s ON s.id = m.session_id
                WHERE s.user_id = ?
                  AND DATE(m.created_at) >= DATE('now', ?)
                GROUP BY DATE(m.created_at)
                ORDER BY day ASC;
                """,
                (user_id, f"-{max(days - 1, 0)} day"),
            ).fetchall()
            return [(str(row["day"]), int(row["total"])) for row in rows]

    def top_sessions_by_message_count(self, user_id: int, limit: int = 5) -> List[tuple[str, int]]:
        with self.database.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT COALESCE(s.title, 'Sesi Baru') AS session_title, COUNT(m.id) AS total
                FROM chat_sessions s
                LEFT JOIN chat_messages m ON m.session_id = s.id
                WHERE s.user_id = ?
                GROUP BY s.id
                ORDER BY total DESC, s.id DESC
                LIMIT ?;
                """,
                (user_id, limit),
            ).fetchall()
            return [(str(row["session_title"]), int(row["total"])) for row in rows]

    def count_messages_in_last_days(self, user_id: int, days: int) -> int:
        if days < 1:
            return 0
        window = f"-{days - 1} day"
        with self.database.get_connection() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS total
                FROM chat_messages m
                JOIN chat_sessions s ON s.id = m.session_id
                WHERE s.user_id = ?
                  AND DATE(m.created_at) >= DATE('now', ?);
                """,
                (user_id, window),
            ).fetchone()
            return int(row["total"]) if row else 0

    def rag_source_frequency(self, user_id: int, limit: int = 10) -> List[Tuple[str, int]]:
        pattern = re.compile(r"`([^`]+)`")
        with self.database.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT m.content
                FROM chat_messages m
                JOIN chat_sessions s ON s.id = m.session_id
                WHERE s.user_id = ?
                  AND m.role = 'assistant'
                  AND m.content LIKE '%Sumber RAG:%';
                """,
                (user_id,),
            ).fetchall()
        counts: Counter[str] = Counter()
        for row in rows:
            content = str(row["content"])
            if "Sumber RAG:" not in content:
                continue
            tail = content.split("Sumber RAG:", 1)[-1]
            for match in pattern.findall(tail):
                name = match.strip()
                if name:
                    counts[name] += 1
        return counts.most_common(limit)
