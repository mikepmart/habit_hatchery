#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime, date, timedelta

import zmq


# =========================
# Core date & bucketing logic
# =========================

def parse_iso_date(value):
    """
    Try to parse a date or datetime string into a date object.
    Returns a datetime.date or None on failure.
    """
    if not isinstance(value, str):
        return None

    # Try full ISO datetime first (handles 'YYYY-MM-DD' and 'YYYY-MM-DDTHH:MM:SS')
    try:
        dt = datetime.fromisoformat(value)
        return dt.date()
    except ValueError:
        pass

    # Fallback to explicit date-only pattern
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def bucket_for_day(d: date) -> str:
    """Day bucket key: YYYY-MM-DD"""
    return d.isoformat()


def bucket_for_week(d: date) -> str:
    """
    Week bucket key: YYYY-MM-DD of the Monday that starts that week.
    Monday is weekday() == 0.
    """
    monday = d - timedelta(days=d.weekday())
    return monday.isoformat()


def bucket_for_month(d: date) -> str:
    """Month bucket key: YYYY-MM"""
    return f"{d.year:04d}-{d.month:02d}"


def get_bucket_key(d: date, bucket_type: str) -> str | None:
    """
    Map a date and bucket_type to a bucket key string.
    """
    if bucket_type == "day":
        return bucket_for_day(d)
    elif bucket_type == "week":
        return bucket_for_week(d)
    elif bucket_type == "month":
        return bucket_for_month(d)
    else:
        return None


def compute_time_buckets(items, date_field: str, bucket_type: str):
    """
    Core logic: given items, a date_field name, and a bucket_type,
    return a dict: bucket_key -> count.

    - Ignores items where date_field is missing or invalid.
    - Only depends on date_field values, not app-specific fields.
    """
    buckets: dict[str, int] = {}

    for item in items:
        raw_date_value = item.get(date_field)
        d = parse_iso_date(raw_date_value)
        if d is None:
            # Skip invalid/missing dates for reliability
            continue

        bucket_key = get_bucket_key(d, bucket_type)
        if bucket_key is None:
            # Invalid bucket_type was already validated, so this is just a safety net
            continue

        buckets[bucket_key] = buckets.get(bucket_key, 0) + 1

    return buckets


# =========================
# Request / response helpers
# =========================

def make_error_response(message):
    return {
        "status": "error",
        "error": message
    }


def make_success_response(bucket_type, date_field, buckets):
    return {
        "status": "ok",
        "bucket_type": bucket_type,
        "date_field": date_field,
        "buckets": buckets
    }


def serialize_response(response_dict):
    """
    Deterministic JSON encoding:
      - sort_keys=True → stable key order
      - separators=(',', ':') → no extra spaces
    """
    return json.dumps(
        response_dict,
        sort_keys=True,
        separators=(",", ":")
    ).encode("utf-8")


def parse_request_bytes(raw_bytes):
    """
    Decode raw bytes into a Python dict, or return an error response.
    """
    try:
        request = json.loads(raw_bytes.decode("utf-8"))
        return request, None
    except json.JSONDecodeError:
        return None, make_error_response("Invalid JSON in request body.")


def validate_request(request):
    """
    Validate input structure; return (bucket_type, date_field, items, error_or_none).
    """
    if request.get("request_type") != "time_series_trend":
        return None, None, None, make_error_response(
            "Unsupported request_type. Expected 'time_series_trend'."
        )

    bucket_type = request.get("bucket_type")
    if bucket_type not in ("day", "week", "month"):
        return None, None, None, make_error_response(
            "Invalid 'bucket_type'. Expected 'day', 'week', or 'month'."
        )

    date_field = request.get("date_field")
    if not isinstance(date_field, str) or not date_field.strip():
        return None, None, None, make_error_response(
            "'date_field' must be a non-empty string."
        )

    items = request.get("items")
    if not isinstance(items, list):
        return None, None, None, make_error_response(
            "'items' field must be a list."
        )

    return bucket_type, date_field, items, None


def handle_message(raw_bytes):
    """
    Pure handler: bytes in → bytes out.
    Use this for unit tests.
    """
    request, parse_error = parse_request_bytes(raw_bytes)
    if parse_error is not None:
        return serialize_response(parse_error)

    bucket_type, date_field, items, validation_error = validate_request(request)
    if validation_error is not None:
        return serialize_response(validation_error)

    buckets = compute_time_buckets(items, date_field, bucket_type)
    response = make_success_response(bucket_type, date_field, buckets)
    return serialize_response(response)


# =========================
# ZeroMQ server & quit logic
# =========================

def create_socket(port: str):
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind(f"tcp://*:{port}")
    return context, socket


def is_quit_signal(raw_request: bytes) -> bool:
    """
    Accept a broader set of quit signals:
    - raw b"q"
    - UTF-8 string "q"
    - JSON string "q" (i.e., b'"q"')
    """
    trimmed = raw_request.strip().lower()
    if trimmed == b"q":
        return True

    try:
        text = trimmed.decode("utf-8")
    except UnicodeDecodeError:
        return False

    if text == "q":
        return True

    try:
        decoded = json.loads(text)
    except json.JSONDecodeError:
        return False

    return isinstance(decoded, str) and decoded.strip().lower() == "q"


def keyboard_quit_pressed() -> bool:
    """
    Non-blocking check for pressing 'q' in the server terminal.
    Works on Windows (msvcrt) and best-effort on POSIX (select).
    """
    try:
        import msvcrt  # Windows-only
    except ImportError:
        msvcrt = None

    if msvcrt:
        if msvcrt.kbhit():
            key = msvcrt.getwch()
            return key.lower() == "q"
        return False

    try:
        import select
        ready, _, _ = select.select([sys.stdin], [], [], 0)
        if ready:
            key = sys.stdin.read(1)
            return key.lower() == "q"
    except (ImportError, OSError, ValueError):
        return False

    return False


def run_server(port="5560"):
    """
    Main server loop.

    - Normal request: JSON → handled by handle_message().
    - Quit request: raw message 'q' (case-insensitive) → respond once, then exit.
    """
    context, socket = create_socket(port)
    socket.setsockopt(zmq.RCVTIMEO, 200)  # periodic wakeups to check keyboard
    print(f"[time-series-trend] Listening on port {port}...", file=sys.stderr)
    print("  Send 'q' from a client or press 'q' in this terminal to quit.", file=sys.stderr)

    try:
        while True:
            if keyboard_quit_pressed():
                print("[time-series-trend] Quit via keyboard input.", file=sys.stderr)
                break

            try:
                raw_request = socket.recv()
            except zmq.Again:
                continue

            # Quit path: user presses 'q' in main program and it sends 'q'
            if is_quit_signal(raw_request):
                quit_response = {
                    "status": "ok",
                    "message": "Time-Series Trend Analyzer shutting down."
                }
                socket.send(serialize_response(quit_response))
                print("[time-series-trend] Received quit signal 'q'. Exiting.",
                      file=sys.stderr)
                break

            try:
                response_bytes = handle_message(raw_request)
            except Exception as e:
                # Just in case something slips through
                error_response = make_error_response(f"Internal error: {str(e)}")
                response_bytes = serialize_response(error_response)

            socket.send(response_bytes)

    except KeyboardInterrupt:
        print("\n[time-series-trend] Interrupted via keyboard.", file=sys.stderr)
    finally:
        socket.close()
        context.term()


def main():
    # Allow override via env var to match your Small Pool conventions
    port = os.getenv("TIME_SERIES_PORT", "5560")
    run_server(port)


if __name__ == "__main__":
    main()
