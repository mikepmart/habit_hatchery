# models.py
from dataclasses import dataclass
from datetime import date

@dataclass
class Habit:
    id: int
    name: str
    schedule: str = "daily"   # "daily" or "weekly:Mon,Wed,Fri"

WEEK = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

def is_scheduled_today(h: Habit, d: date) -> bool:
    if h.schedule == "daily":
        return True
    if h.schedule.startswith("weekly:"):
        days = h.schedule.split(":", 1)[1].split(",")
        return WEEK[d.weekday()] in [x.strip() for x in days]
    return True