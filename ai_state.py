import json
import os
import sqlite3
from typing import Any, Dict, Optional

CONFIG_PATH = "assistant_settings.json"
TRAINING_LOG_PATH = "training_history.json"


def get_default_config() -> Dict[str, str]:
    return {
        "resource": "wood",
        "db_path": "assistant.db",
        "remote_url": "",
        "video_path": "",
        "ai_mode": "local",
        "device": "poco_f5",
    }


def load_config(path: Optional[str] = None) -> Dict[str, str]:
    config_path = path or CONFIG_PATH
    if not os.path.exists(config_path):
        return get_default_config()
    try:
        with open(config_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        merged = get_default_config()
        merged.update({k: str(v) for k, v in data.items() if isinstance(v, (str, int, float, bool))})
        return merged
    except Exception:
        return get_default_config()


def save_config(config: Dict[str, Any], path: Optional[str] = None) -> None:
    config_path = path or CONFIG_PATH
    with open(config_path, "w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2)


def ensure_training_db(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS training_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type TEXT NOT NULL,
            source_value TEXT NOT NULL,
            resource_name TEXT NOT NULL,
            details TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def record_training_event(config: Dict[str, Any], source_type: str, source_value: str, resource_name: str, details: str) -> Dict[str, Any]:
    db_path = config.get("db_path", "assistant.db")
    ensure_training_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        "INSERT INTO training_events (source_type, source_value, resource_name, details) VALUES (?, ?, ?, ?)",
        (source_type, source_value, resource_name, details),
    )
    row_id = cursor.lastrowid
    conn.commit()
    conn.close()

    entry = {
        "id": row_id,
        "source_type": source_type,
        "source_value": source_value,
        "resource_name": resource_name,
        "details": details,
    }

    if os.path.exists(TRAINING_LOG_PATH):
        with open(TRAINING_LOG_PATH, "r", encoding="utf-8") as handle:
            try:
                items = json.load(handle)
            except Exception:
                items = []
    else:
        items = []

    if not isinstance(items, list):
        items = []
    items.append(entry)
    with open(TRAINING_LOG_PATH, "w", encoding="utf-8") as handle:
        json.dump(items, handle, indent=2)

    return entry
