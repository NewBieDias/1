#!/usr/bin/env python3
import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime
from typing import Optional, Tuple

import cv2
import numpy as np
import requests
from mss import mss

from agent_core import AgentMemory, DecisionEngine
from device_profiles import get_screen_preset


class LocalResourceDB:
    def __init__(self, db_path: str = "assistant.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS resources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                mode TEXT NOT NULL DEFAULT 'hsv',
                hsv_lower TEXT,
                hsv_upper TEXT,
                template_path TEXT,
                threshold REAL NOT NULL DEFAULT 0.8,
                action TEXT NOT NULL DEFAULT 'collect',
                description TEXT,
                notes TEXT,
                priority INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resource_name TEXT NOT NULL,
                status TEXT NOT NULL,
                details TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS learned_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resource_name TEXT NOT NULL,
                hsv_value TEXT NOT NULL,
                success INTEGER NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.conn.commit()

    def seed_defaults(self) -> None:
        defaults = [
            ("wood", "hsv", "[20, 100, 100]", "[40, 255, 255]", None, 0.8, "collect", "Wood", "Use for wood nodes", 3),
            ("stone", "hsv", "[0, 100, 100]", "[20, 255, 255]", None, 0.8, "collect", "Stone", "Use for stone nodes", 2),
            ("fiber", "hsv", "[35, 100, 100]", "[60, 255, 255]", None, 0.8, "collect", "Fiber", "Use for fiber nodes", 1),
            ("hide", "hsv", "[170, 100, 100]", "[180, 255, 255]", None, 0.8, "collect", "Hide", "Use for hide nodes", 1),
        ]
        for row in defaults:
            name, mode, lower, upper, template_path, threshold, action, description, notes, priority = row
            self.conn.execute(
                """
                INSERT OR IGNORE INTO resources (
                    name, mode, hsv_lower, hsv_upper, template_path, threshold, action, description, notes, priority
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (name, mode, lower, upper, template_path, threshold, action, description, notes, priority),
            )
        self.conn.commit()

    def import_from_json(self, json_path: str) -> None:
        if not os.path.exists(json_path):
            return
        with open(json_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        for entry in data.get("resources", []):
            self.conn.execute(
                """
                INSERT OR REPLACE INTO resources (
                    name, mode, hsv_lower, hsv_upper, template_path, threshold, action, description, notes, priority
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry["name"],
                    entry.get("mode", "hsv"),
                    json.dumps(entry.get("hsv_lower", [])),
                    json.dumps(entry.get("hsv_upper", [])),
                    entry.get("template_path"),
                    entry.get("threshold", 0.8),
                    entry.get("action", "collect"),
                    entry.get("description", ""),
                    entry.get("notes", ""),
                    entry.get("priority", 0),
                ),
            )
        self.conn.commit()

    def list_resources(self):
        rows = self.conn.execute("SELECT name, mode, action, description, priority FROM resources ORDER BY priority DESC, name").fetchall()
        return [dict(row) for row in rows]

    def get_resource(self, name: str):
        row = self.conn.execute(
            "SELECT name, mode, hsv_lower, hsv_upper, template_path, threshold, action, description, notes, priority FROM resources WHERE name = ?",
            (name,),
        ).fetchone()
        return dict(row) if row else None

    def all_resources(self):
        rows = self.conn.execute("SELECT name, mode, hsv_lower, hsv_upper, template_path, threshold, action, description, notes, priority FROM resources ORDER BY priority DESC, name").fetchall()
        return [dict(row) for row in rows]

    def log_event(self, resource_name: str, status: str, details: str) -> None:
        self.conn.execute(
            "INSERT INTO events (resource_name, status, details) VALUES (?, ?, ?)",
            (resource_name, status, details),
        )
        self.conn.commit()

    def record_learning(self, resource_name: str, hsv_value: Optional[Tuple[int, int, int]], success: bool) -> None:
        if not hsv_value:
            return
        self.conn.execute(
            "INSERT INTO learned_samples (resource_name, hsv_value, success) VALUES (?, ?, ?)",
            (resource_name, json.dumps(list(hsv_value)), 1 if success else 0),
        )
        self.conn.commit()
        self._adapt_resource_from_sample(resource_name, hsv_value, success)

    def _adapt_resource_from_sample(self, resource_name: str, hsv_value: Tuple[int, int, int], success: bool) -> None:
        resource = self.get_resource(resource_name)
        if not resource or resource.get("mode") != "hsv":
            return
        if not success:
            return
        base_lower = np.array(json.loads(resource["hsv_lower"] or "[0, 0, 0]"), dtype=int)
        base_upper = np.array(json.loads(resource["hsv_upper"] or "[179, 255, 255]"), dtype=int)
        sample = np.array(hsv_value, dtype=int)

        new_lower = np.array([
            max(0, min(base_lower[0], sample[0] - 12)),
            max(0, min(base_lower[1], sample[1] - 35)),
            max(0, min(base_lower[2], sample[2] - 35)),
        ], dtype=int)
        new_upper = np.array([
            min(179, max(base_upper[0], sample[0] + 12)),
            min(255, max(base_upper[1], sample[1] + 35)),
            min(255, max(base_upper[2], sample[2] + 35)),
        ], dtype=int)

        self.conn.execute(
            "UPDATE resources SET hsv_lower = ?, hsv_upper = ?, notes = ? WHERE name = ?",
            (
                json.dumps(new_lower.tolist()),
                json.dumps(new_upper.tolist()),
                f"Learned from {self._history_for(resource_name)} samples",
                resource_name,
            ),
        )
        self.conn.commit()

    def _history_for(self, resource_name: str) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) as cnt FROM learned_samples WHERE resource_name = ?",
            (resource_name,),
        ).fetchone()
        return int(row["cnt"] if row else 0)


class VisionEngine:
    def __init__(self, monitor: int = 1, screenshots_dir: str = "screenshots"):
        self.monitor = monitor
        self.screenshots_dir = screenshots_dir
        os.makedirs(self.screenshots_dir, exist_ok=True)
        self.sct = mss()

    def capture_frame(self) -> np.ndarray:
        screenshot = self.sct.grab(self.sct.monitors[self.monitor])
        frame = np.array(screenshot)
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

    def save_frame(self, frame: np.ndarray, label: str) -> str:
        filename = os.path.join(self.screenshots_dir, f"{label}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.png")
        cv2.imwrite(filename, frame)
        return filename

    def _find_by_hsv(self, frame: np.ndarray, resource: dict) -> Optional[Tuple[Tuple[int, int], Tuple[int, int, int]]]:
        if not resource.get("hsv_lower") or not resource.get("hsv_upper"):
            return None
        lower = np.array(json.loads(resource["hsv_lower"]), dtype=np.uint8)
        upper = np.array(json.loads(resource["hsv_upper"]), dtype=np.uint8)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, lower, upper)
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        largest = max(contours, key=cv2.contourArea)
        if cv2.contourArea(largest) < 100:
            return None

        x, y, w, h = cv2.boundingRect(largest)
        roi = hsv[y:y + h, x:x + w]
        mean_hsv = cv2.mean(roi)
        return ((x + w // 2, y + h // 2), (int(mean_hsv[0]), int(mean_hsv[1]), int(mean_hsv[2])))

    def _find_by_template(self, frame: np.ndarray, resource: dict) -> Optional[Tuple[Tuple[int, int], Tuple[int, int, int]]]:
        template_path = resource.get("template_path")
        if not template_path or not os.path.exists(template_path):
            return None
        template = cv2.imread(template_path, cv2.IMREAD_COLOR)
        if template is None:
            return None
        result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val < float(resource.get("threshold", 0.8)):
            return None
        x, y = max_loc
        h, w = template.shape[:2]
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        roi = hsv[y:y + h, x:x + w]
        mean_hsv = cv2.mean(roi)
        return ((x + w // 2, y + h // 2), (int(mean_hsv[0]), int(mean_hsv[1]), int(mean_hsv[2])))

    def find_resource(self, frame: np.ndarray, resource: dict) -> Optional[Tuple[Tuple[int, int], Tuple[int, int, int]]]:
        if resource.get("mode") == "template":
            return self._find_by_template(frame, resource)
        return self._find_by_hsv(frame, resource)

    def click(self, point: Tuple[int, int]) -> None:
        try:
            import pyautogui
        except Exception:
            print("pyautogui is not available; skipping click")
            return
        pyautogui.moveTo(point[0], point[1], duration=0.1)
        pyautogui.click(point[0], point[1])


class RemoteSync:
    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None):
        self.base_url = base_url or os.getenv("REMOTE_SYNC_URL")
        self.token = token or os.getenv("REMOTE_SYNC_TOKEN")

    def push(self, resource_name: str, status: str, details: str) -> None:
        if not self.base_url:
            return
        payload = {"resource_name": resource_name, "status": status, "details": details}
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            requests.post(self.base_url, json=payload, headers=headers, timeout=5)
        except Exception as exc:
            print(f"Remote sync failed: {exc}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Albion Online helper with priority selection and screenshots")
    parser.add_argument("--resource", default=None, help="Specific resource name to target")
    parser.add_argument("--once", action="store_true", help="Run one detection cycle")
    parser.add_argument("--db", default="assistant.db", help="Path to local SQLite DB")
    parser.add_argument("--config", default="albion_resources.json", help="Path to JSON resource definitions")
    parser.add_argument("--monitor", type=int, default=1, help="MSS monitor index")
    parser.add_argument("--device", default="poco_f5", help="Screen preset name, e.g. poco_f5")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    db = LocalResourceDB(args.db)
    db.seed_defaults()
    if os.path.exists(args.config):
        db.import_from_json(args.config)

    vision = VisionEngine(monitor=args.monitor)
    sync = RemoteSync()
    memory = AgentMemory("agent_memory.db")
    decision_engine = DecisionEngine(memory)

    preset = get_screen_preset(args.device)
    print(f"Using screen preset: {preset['name']} ({preset['resolution']}, {preset['aspect_ratio']})")
    print("Loaded resources:")
    for resource in db.list_resources():
        print(f" - {resource['name']} (priority={resource['priority']}): {resource['description']}")

    print("Starting priority loop. Press Ctrl+C to stop.")
    while True:
        frame = vision.capture_frame()
        resources = db.all_resources()
        if args.resource:
            resources = [r for r in resources if r["name"] == args.resource]

        chosen = decision_engine.choose_resource(resources)
        if chosen is None:
            print("No resources configured")
            break

        detection = vision.find_resource(frame, chosen)
        if detection:
            point, hsv_mean = detection
            print(f"AI chose {chosen['name']} at {point} with HSV {hsv_mean}")
            vision.save_frame(frame, chosen['name'])
            vision.click(point)
            db.log_event(chosen['name'], "detected", json.dumps({"point": point, "hsv_mean": hsv_mean}))
            db.record_learning(chosen['name'], hsv_mean, success=True)
            sync.push(chosen['name'], "detected", json.dumps({"point": point, "hsv_mean": hsv_mean}))
        else:
            print(f"{chosen['name']} not found")
            db.log_event(chosen['name'], "missed", "No resource found")

        if args.once:
            break
        time.sleep(2)

    return 0


if __name__ == "__main__":
    sys.exit(main())
