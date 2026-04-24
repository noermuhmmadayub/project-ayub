from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from passlib.context import CryptContext

from src.database.connection import DatabaseConnection


@dataclass(frozen=True)
class ChatSession:
    id: int
    title: str
    started_at: str
    is_pinned: bool


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str
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

    def _ensure_schema_migrations(self) -> None:
        with self.database.get_connection() as conn:
            columns = conn.execute("PRAGMA table_info(chat_sessions);").fetchall()
            has_is_pinned = any(str(col["name"]) == "is_pinned" for col in columns)
            if not has_is_pinned:
                conn.execute(
                    "ALTER TABLE chat_sessions ADD COLUMN is_pinned INTEGER NOT NULL DEFAULT 0;"
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
                "SELECT id, username, password_hash FROM users WHERE username = ?;",
                (username,),
            ).fetchone()
            return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        with self.database.get_connection() as conn:
            row = conn.execute(
                "SELECT id, username, password_hash FROM users WHERE id = ?;",
                (user_id,),
            ).fetchone()
            return dict(row) if row else None

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
                SELECT id, COALESCE(title, 'Sesi Baru') AS title, started_at, is_pinned
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
                )
                for row in rows
            ]

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
                SELECT role, content, created_at
                FROM chat_messages
                WHERE session_id = ?
                ORDER BY id ASC;
                """,
                (session_id,),
            ).fetchall()
            return [
                ChatMessage(
                    role=str(row["role"]),
                    content=str(row["content"]),
                    created_at=str(row["created_at"]),
                )
                for row in rows
            ]

    def save_message(self, session_id: int, role: str, content: str) -> None:
        with self.database.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO chat_messages (session_id, role, content)
                VALUES (?, ?, ?);
                """,
                (session_id, role, content),
            )

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
