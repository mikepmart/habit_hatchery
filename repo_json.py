# repo_json.py
import json, os
from datetime import date
from typing import List, Dict, Set
from models import Habit, is_scheduled_today

class JSONRepo:
    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not os.path.exists(path):
            self._write({"next_id": 1, "habits": [], "completions": {}})
        self.data = self._read()

    def _read(self):
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write(self, obj):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2)
        os.replace(tmp, self.path)

    # -------- Habits --------
    def list_habits(self) -> List[Habit]:
        return [Habit(**h) for h in self.data["habits"]]

    def add_habit(self, name: str, schedule: str):
        nid = self.data["next_id"]
        self.data["next_id"] += 1
        self.data["habits"].append({"id": nid, "name": name, "schedule": schedule})
        self._write(self.data)

    # -------- Scheduling / Today --------
    def habits_for_today(self, d: date) -> List[Habit]:
        return [h for h in self.list_habits() if is_scheduled_today(h, d)]

    # -------- Completions --------
    def completed_ids(self, d: date) -> Set[int]:
        key = d.isoformat()
        ids = self.data["completions"].get(key, [])
        return set(ids)

    def set_completed(self, habit_id: int, d: date, done: bool):
        key = d.isoformat()
        ids: List[int] = self.data["completions"].get(key, [])
        if done and habit_id not in ids:
            ids.append(habit_id)
        if not done and habit_id in ids:
            ids.remove(habit_id)
        self.data["completions"][key] = ids
        self._write(self.data)

    def delete_habit(self, habit_id: int):
        # remove from habits
        self.data["habits"] = [h for h in self.data["habits"] if h["id"] != habit_id]
        # remove any completions referencing it
        for day, ids in list(self.data["completions"].items()):
            new_ids = [i for i in ids if i != habit_id]
            if new_ids:
                self.data["completions"][day] = new_ids
            else:
                # optional: drop empty day entries to keep file tidy
                self.data["completions"].pop(day, None)
        self._write(self.data)