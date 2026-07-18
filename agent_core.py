import json
import os
import sqlite3
from typing import List, Dict, Optional, Tuple


class AgentMemory:
    def __init__(self, db_path: str = 'agent_memory.db'):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resource_name TEXT NOT NULL,
                score REAL NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def save_decision(self, resource_name: str, score: float, reason: str) -> None:
        self.conn.execute('INSERT INTO decisions(resource_name, score, reason) VALUES (?, ?, ?)', (resource_name, score, reason))
        self.conn.commit()

    def get_history(self, resource_name: str) -> List[Dict]:
        rows = self.conn.execute('SELECT resource_name, score, reason, created_at FROM decisions WHERE resource_name=? ORDER BY id DESC LIMIT 10', (resource_name,)).fetchall()
        return [dict(r) for r in rows]


class DecisionEngine:
    def __init__(self, memory: AgentMemory):
        self.memory = memory

    def choose_resource(self, resources: List[Dict]) -> Optional[Dict]:
        if not resources:
            return None
        scored = []
        for resource in resources:
            history = self.memory.get_history(resource['name'])
            score = float(resource.get('priority', 0))
            if history:
                score += sum(item['score'] for item in history) / max(1, len(history))
            scored.append((score, resource))
        scored.sort(reverse=True)
        best = scored[0][1]
        self.memory.save_decision(best['name'], scored[0][0], 'priority+memory')
        return best
