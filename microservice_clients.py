"""Helpers to call the ZeroMQ microservices from the Tk application."""

from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Dict, List

import zmq

from models import Habit

DEFAULT_PORTS = {
    "streaks": 5555,
    "trend": 5560,
    "activity": 5562,
    "progress": 5564,
}

TIMEOUT_MS = 1500
_CONTEXT = zmq.Context.instance()


# ---------- Low-level send helpers ----------
def _make_socket(port: int):
    socket = _CONTEXT.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, TIMEOUT_MS)
    socket.setsockopt(zmq.SNDTIMEO, TIMEOUT_MS)
    socket.setsockopt(zmq.LINGER, 0)
    socket.connect(f"tcp://localhost:{port}")
    return socket


def _send_json(port: int, payload: dict):
    socket = _make_socket(port)
    try:
        socket.send_json(payload)
        return socket.recv_json(), None
    except zmq.error.Again:
        return None, f"Timed out contacting service on port {port}."
    except Exception as exc:  # pragma: no cover - defensive
        return None, f"Service error on port {port}: {exc}"
    finally:
        socket.close()


def _send_bytes(port: int, payload: dict):
    socket = _make_socket(port)
    try:
        socket.send_string(json.dumps(payload))
        raw = socket.recv()
        return json.loads(raw.decode("utf-8")), None
    except zmq.error.Again:
        return None, f"Timed out contacting service on port {port}."
    except Exception as exc:  # pragma: no cover - defensive
        return None, f"Service error on port {port}: {exc}"
    finally:
        socket.close()


# ---------- Microservice callers ----------
def streaks_for_dates(date_strings: List[str], port: int = DEFAULT_PORTS["streaks"]):
    """Call the streaks microservice for a list of completion date strings."""
    if not date_strings:
        return None, "No completions yet."

    response, error = _send_json(port, {"dates": date_strings})
    if error:
        return None, error
    if not response.get("ok"):
        return None, response.get("error", "Unknown streaks error.")
    return response.get("result", {}), None


def progress_overview(
    current: int,
    target: int,
    goals: List[dict],
    mode: str = "both",
    port: int = DEFAULT_PORTS["progress"],
):
    payload = {
        "request_type": "progress_goal",
        "mode": mode,
        "current": current,
        "target": target,
        "goals": goals,
    }
    response, error = _send_bytes(port, payload)
    if error:
        return None, error
    if response.get("status") != "ok":
        return None, response.get("error", "Unknown progress error.")
    return response, None


def activity_overview(
    items: List[dict],
    date_field: str,
    range_start: str,
    range_end: str,
    mode: str = "both",
    port: int = DEFAULT_PORTS["activity"],
):
    if not items:
        return None, "No completion history yet."

    payload = {
        "request_type": "activity_analyzer",
        "mode": mode,
        "date_field": date_field,
        "items": items,
        "range_start": range_start,
        "range_end": range_end,
    }
    response, error = _send_bytes(port, payload)
    if error:
        return None, error
    if response.get("status") != "ok":
        return None, response.get("error", "Unknown activity analyzer error.")
    return response, None


def trend_overview(
    items: List[dict],
    date_field: str,
    bucket_type: str = "week",
    port: int = DEFAULT_PORTS["trend"],
):
    if not items:
        return None, "No completion history yet."
    payload = {
        "request_type": "time_series_trend",
        "bucket_type": bucket_type,
        "date_field": date_field,
        "items": items,
    }
    response, error = _send_bytes(port, payload)
    if error:
        return None, error
    if response.get("status") != "ok":
        return None, response.get("error", "Unknown trend analyzer error.")
    return response, None


# ---------- Data shaping helpers ----------
def _completion_items(repo) -> List[dict]:
    """Flatten completion history into items for analytics calls."""
    habit_lookup: Dict[int, Habit] = {h.id: h for h in repo.list_habits()}
    items: List[dict] = []
    for day, ids in repo.data["completions"].items():
        for hid in ids:
            habit = habit_lookup.get(hid)
            if habit:
                items.append(
                    {"habit_id": hid, "habit_name": habit.name, "completed_on": day}
                )
    return items


def _progress_inputs(repo):
    today = date.today()
    habits_today = repo.habits_for_today(today)
    completed_today = repo.completed_ids(today)
    goals = []

    for habit in habits_today:
        goals.append(
            {
                "id": habit.id,
                "label": habit.name,
                "current": 1 if habit.id in completed_today else 0,
                "target": 1,
            }
        )

    return {
        "current": len(completed_today),
        "target": len(habits_today),
        "goals": goals,
    }


# ---------- Public aggregation ----------
def gather_microservice_snapshot(repo):
    """
    Collects all analytics data in one call so the UI can refresh quickly.
    Returns a dict with keys: progress, streaks, activity, trend.
    """
    snapshot = {
        "progress": {"response": None, "error": None},
        "streaks": {"entries": [], "error": None},
        "activity": {"response": None, "error": None},
        "trend": {"response": None, "error": None},
    }

    # Progress
    progress_payload = _progress_inputs(repo)
    progress_resp, progress_err = progress_overview(**progress_payload)
    snapshot["progress"]["response"] = progress_resp
    snapshot["progress"]["error"] = progress_err

    # Streaks (per habit)
    dates_by_habit = repo.completion_dates_by_habit()
    for habit in repo.list_habits():
        result, streak_err = streaks_for_dates(dates_by_habit.get(habit.id, []))
        snapshot["streaks"]["entries"].append(
            {
                "habit": habit,
                "result": result,
                "error": streak_err,
            }
        )

    # Activity analyzer (aggregate)
    activity_items = _completion_items(repo)
    range_end = date.today()
    range_start = range_end - timedelta(days=13)
    activity_resp, activity_err = activity_overview(
        items=activity_items,
        date_field="completed_on",
        range_start=range_start.isoformat(),
        range_end=range_end.isoformat(),
    )
    snapshot["activity"]["response"] = activity_resp
    snapshot["activity"]["error"] = activity_err

    # Trend analyzer
    trend_resp, trend_err = trend_overview(
        items=activity_items,
        date_field="completed_on",
        bucket_type="week",
    )
    snapshot["trend"]["response"] = trend_resp
    snapshot["trend"]["error"] = trend_err

    return snapshot
