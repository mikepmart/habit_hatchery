#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime, date, timedelta

import zmq


# =========================
# Date parsing helpers
# =========================

def parse_iso_date(value):
    """
    Parse a 'YYYY-MM-DD' or ISO date/datetime string into a datetime.date.
    Returns datetime.date or None on failure.
    """
    if not isinstance(value, str):
        return None

    # Try datetime.fromisoformat (handles YYYY-MM-DD and many ISO strings)
    try:
        dt = datetime.fromisoformat(value)
        return dt.date()
    except ValueError:
        pass

    # Fallback to strict date-only format
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


# =========================
# Core logic: Longest run
# =========================

def extract_unique_dates(items, date_field):
    """
    Extract a sorted list of unique dates from items[date_field].
    Invalid or missing dates are ignored.
    """
    dates_set = set()

    for item in items:
        raw_date = item.get(date_field)
        d = parse_iso_date(raw_date)
        if d is not None:
            dates_set.add(d)

    return sorted(dates_set)


def find_longest_active_run(dates):
    """
    Given a sorted list of unique datetime.date objects, find the longest
    consecutive run of days.

    Returns a dict:
      {
        "length_days": int,
        "start_date": "YYYY-MM-DD" or None,
        "end_date": "YYYY-MM-DD" or None
      }

    If there are multiple runs with the same max length, the earliest run
    (by start_date) is chosen for deterministic behavior.
    """
    if not dates:
        return {
            "length_days": 0,
            "start_date": None,
            "end_date": None
        }

    best_length = 1
    best_start = dates[0]
    best_end = dates[0]

    current_start = dates[0]
    current_end = dates[0]
    current_length = 1

    for i in range(1, len(dates)):
        prev = dates[i - 1]
        curr = dates[i]
        if curr == prev + timedelta(days=1):
            # Continue the streak
            current_end = curr
            current_length += 1
        else:
            # Streak ended, compare with best
            if current_length > best_length:
                best_length = current_length
                best_start = current_start
                best_end = current_end
            # If equal length, keep existing best (earlier run wins)

            # Start new streak
            current_start = curr
            current_end = curr
            current_length = 1

    # Final comparison after loop
    if current_length > best_length:
        best_length = current_length
        best_start = current_start
        best_end = current_end

    return {
        "length_days": best_length,
        "start_date": best_start.isoformat(),
        "end_date": best_end.isoformat()
    }


def compute_longest_run(items, date_field):
    """
    High-level helper: items + date_field -> longest_run dict.
    """
    dates = extract_unique_dates(items, date_field)
    if not dates:
        return {
            "length_days": 0,
            "start_date": None,
            "end_date": None
        }
    return find_longest_active_run(dates)


# =========================
# Core logic: Heatmap
# =========================

def build_date_range(start_date, end_date):
    """
    Inclusive date range generator: start_date..end_date.
    """
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def compute_heatmap(items, date_field, range_start_str, range_end_str):
    """
    Given items, date_field, and a date range (strings), build a heatmap:
      { "YYYY-MM-DD": count }

    Every date in [range_start, range_end] is present, with 0 as default count.
    """
    start_date = parse_iso_date(range_start_str)
    end_date = parse_iso_date(range_end_str)

    if start_date is None or end_date is None:
        return None, make_error_response(
            "'range_start' and 'range_end' must be valid ISO dates (YYYY-MM-DD)."
        )

    if end_date < start_date:
        return None, make_error_response(
            "'range_end' must be on or after 'range_start'."
        )

    # Initialize all dates in range with 0
    heatmap = {
        d.isoformat(): 0
        for d in build_date_range(start_date, end_date)
    }

    # Count items per day (only those within range)
    for item in items:
        raw_date = item.get(date_field)
        d = parse_iso_date(raw_date)
        if d is None:
            continue
        key = d.isoformat()
        if key in heatmap:
            heatmap[key] += 1

    return heatmap, None


# =========================
# Request / Response helpers
# =========================

def make_error_response(message):
    return {
        "status": "error",
        "error": message
    }


def make_success_response(mode, date_field, longest_run, heatmap):
    """
    Standard success response.
    Always includes both 'longest_run' and 'heatmap' keys for stability.
    """
    return {
        "status": "ok",
        "mode": mode,
        "date_field": date_field,
        "longest_run": longest_run,
        "heatmap": heatmap
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
    Validate top-level request structure.
    Returns (mode, date_field, items, error_or_none).
    """
    if request.get("request_type") != "activity_analyzer":
        return None, None, None, make_error_response(
            "Unsupported request_type. Expected 'activity_analyzer'."
        )

    mode = request.get("mode", "both")
    if mode not in ("longest_run", "heatmap", "both"):
        return None, None, None, make_error_response(
            "Invalid 'mode'. Expected 'longest_run', 'heatmap', or 'both'."
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

    return mode, date_field, items, None


def handle_message(raw_bytes):
    """
    Pure handler: bytes in → bytes out.
    This is easy to unit-test or call from a simple client.
    """
    request, parse_error = parse_request_bytes(raw_bytes)
    if parse_error is not None:
        return serialize_response(parse_error)

    mode, date_field, items, validation_error = validate_request(request)
    if validation_error is not None:
        return serialize_response(validation_error)

    # Prepare outputs
    longest_run = {
        "length_days": 0,
        "start_date": None,
        "end_date": None
    }
    heatmap = {}

    # Longest run
    if mode in ("longest_run", "both"):
        longest_run = compute_longest_run(items, date_field)

    # Heatmap
    if mode in ("heatmap", "both"):
        range_start_str = request.get("range_start")
        range_end_str = request.get("range_end")
        if not range_start_str or not range_end_str:
            return serialize_response(make_error_response(
                "'range_start' and 'range_end' are required for 'heatmap' or 'both' modes."
            ))
        heatmap, heatmap_error = compute_heatmap(
            items, date_field, range_start_str, range_end_str
        )
        if heatmap_error is not None:
            return serialize_response(heatmap_error)

    response = make_success_response(mode, date_field, longest_run, heatmap)
    return serialize_response(response)


# =========================
# ZeroMQ server
# =========================

def create_socket(port):
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind(f"tcp://*:{port}")
    return context, socket


def run_server(port="5562"):
    """
    Main server loop.

    This one does NOT include 'q' to quit by default.
    (Happy to add it if you want the same pattern.)
    """
    context, socket = create_socket(port)
    print(f"[activity-analyzer] Listening on port {port}...", file=sys.stderr)

    try:
        while True:
            raw_request = socket.recv()
            try:
                response_bytes = handle_message(raw_request)
            except Exception as e:
                error_response = make_error_response(f"Internal error: {str(e)}")
                response_bytes = serialize_response(error_response)

            socket.send(response_bytes)

    except KeyboardInterrupt:
        print("\n[activity-analyzer] Interrupted via keyboard.", file=sys.stderr)
    finally:
        socket.close()
        context.term()


def main():
    port = os.getenv("ACTIVITY_ANALYZER_PORT", "5562")
    run_server(port)


if __name__ == "__main__":
    main()
