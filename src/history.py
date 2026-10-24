import sqlite3
from pathlib import Path

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage

HISTORY_LIMIT = 40


class StoredMessage:
    def __init__(self, message_id: int, user_label: str, role: str, text: str):
        self.message_id = message_id
        self.user_label = user_label
        self.role = role
        self.text = text


class History:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                chat_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                user_label TEXT NOT NULL,
                role TEXT NOT NULL,
                text TEXT NOT NULL,
                PRIMARY KEY (chat_id, message_id)
            )
            """
        )
        self._conn.commit()

    def add(self, chat_id: int, message_id: int, user_label: str, role: str, text: str) -> bool:
        cursor = self._conn.execute(
            """
            INSERT OR IGNORE INTO messages (chat_id, message_id, user_label, role, text)
            VALUES (?, ?, ?, ?, ?)
            """,
            (chat_id, message_id, user_label, role, text),
        )
        self._conn.commit()
        return cursor.rowcount == 1

    def recent(self, chat_id: int, limit: int = HISTORY_LIMIT) -> list[StoredMessage]:
        rows = self._conn.execute(
            """
            SELECT message_id, user_label, role, text
            FROM messages
            WHERE chat_id = ?
            ORDER BY message_id DESC
            LIMIT ?
            """,
            (chat_id, limit),
        ).fetchall()
        rows.reverse()
        return [StoredMessage(*row) for row in rows]

    def as_model_messages(self, chat_id: int, limit: int = HISTORY_LIMIT) -> list[AnyMessage]:
        messages: list[AnyMessage] = []
        for row in self.recent(chat_id, limit=limit):
            if row.role == "assistant":
                messages.append(AIMessage(content=row.text))
            else:
                messages.append(HumanMessage(content=f"{row.user_label}: {row.text}"))
        return messages
