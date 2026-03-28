import sqlite3
import json
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone


DB_PATH = "runtime/state.db"


class Storage:
    """
    SQLite-backed persistence layer.
    Stores:
    - state (key/value JSON)
    - goals tree (hierarchical)
    - full message history
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    # ------------------------------------------------------------------
    # DB Initialization
    # ------------------------------------------------------------------
    def _init_db(self) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS state (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS goals (
                    id INTEGER PRIMARY KEY,
                    parent_id INTEGER,
                    goal TEXT,
                    steps TEXT,
                    plan TEXT,
                    status TEXT,
                    created_at TEXT
                )
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY,
                    user_message TEXT,
                    assistant_message TEXT,
                    timestamp TEXT
                )
                """
            )

            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------
    def load_state(self) -> Dict[str, Any]:
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute("SELECT key, value FROM state")
            rows = cur.fetchall()
        finally:
            conn.close()

        state = {}
        for key, value in rows:
            state[key] = json.loads(value)

        return state

    def save_state(self, state: Dict[str, Any]) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            for key, value in state.items():
                cur.execute(
                    """
                    INSERT INTO state (key, value)
                    VALUES (?, ?)
                    ON CONFLICT(key) DO UPDATE SET value=excluded.value
                    """,
                    (key, json.dumps(value)),
                )
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Goals Tree
    # ------------------------------------------------------------------
    def load_goals_tree(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, parent_id, goal, steps, plan, status, created_at FROM goals")
            rows = cur.fetchall()
        finally:
            conn.close()

        # Build nodes
        nodes = {}
        for row in rows:
            node_id, parent_id, goal, steps, plan, status, created_at = row
            nodes[node_id] = {
                "id": node_id,
                "parent_id": parent_id,
                "goal": goal,
                "steps": json.loads(steps) if steps else [],
                "plan": plan,
                "status": status,
                "created_at": created_at,
                "subgoals": [],
            }

        # Build tree
        tree = []
        for node in nodes.values():
            pid = node["parent_id"]
            if pid is not None and pid in nodes:
                nodes[pid]["subgoals"].append(node)
            else:
                tree.append(node)

        return tree

    def save_goals_tree(self, tree: List[Dict[str, Any]]) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM goals")

            def insert_node(node: Dict[str, Any], parent_id: Optional[int]):
                cur.execute(
                    """
                    INSERT INTO goals (id, parent_id, goal, steps, plan, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        node["id"],
                        parent_id,
                        node.get("goal", ""),
                        json.dumps(node.get("steps", [])),
                        node.get("plan", ""),
                        node.get("status", "active"),
                        node.get("created_at", datetime.now(timezone.utc).isoformat()),
                    ),
                )
                for sub in node.get("subgoals", []):
                    insert_node(sub, node["id"])

            for root in tree:
                insert_node(root, None)

            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------
    def load_history(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute("SELECT user_message, assistant_message, timestamp FROM history ORDER BY id ASC")
            rows = cur.fetchall()
        finally:
            conn.close()

        return [
            {
                "user": user,
                "assistant": assistant,
                "timestamp": ts,
            }
            for user, assistant, ts in rows
        ]

    def append_history(self, user: str, assistant: str) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO history (user_message, assistant_message, timestamp)
                VALUES (?, ?, ?)
                """,
                (user, assistant, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
        finally:
            conn.close()
