#!/usr/bin/env python3
import json
import os
import sys

import zmq


# =========================
# Core progress logic
# =========================

def to_float(value):
    """
    Try to convert a value to float.
    Returns (float_value, error_message_or_None).
    """
    try:
        return float(value), None
    except (TypeError, ValueError):
        return None, f"Value '{value}' is not a valid number."


def compute_progress(current, target):
    """
    Given numeric current and target, compute:
      - percent_complete (float, rounded to 2 decimals)
      - completed (bool)
      - status (string)
    """
    # Handle target == 0 to avoid division by zero.
    if target == 0:
        # If the target is 0, treat "current >= target" as completed.
        percent = 100.0 if current >= target else 0.0
        completed = current >= target
    else:
        percent = (current / target) * 100.0
        completed = current >= target

    percent_rounded = round(percent, 2)

    if completed:
        status = "completed"
    elif current <= 0:
        status = "not_started"
    else:
        status = "in_progress"

    return {
        "current": current,
        "target": target,
        "percent_complete": percent_rounded,
        "completed": completed,
        "status": status
    }


def compute_single_goal(current_raw, target_raw):
    """
    Compute progress for a single (current, target) pair.
    Returns (result_dict, error_response_or_None).
    """
    current, err_c = to_float(current_raw)
    if err_c is not None:
        return None, make_error_response(f"Invalid 'current' value: {err_c}")

    target, err_t = to_float(target_raw)
    if err_t is not None:
        return None, make_error_response(f"Invalid 'target' value: {err_t}")

    result = compute_progress(current, target)
    return result, None


def compute_multi_goals(goals):
    """
    Compute progress for an array of goals.
    Each goal object should have:
      - 'current'
      - 'target'
      - optional 'id'
      - optional 'label'

    Returns (list_of_goal_summaries, error_response_or_None).
    """
    summaries = []

    for idx, goal in enumerate(goals):
        # Extract fields
        current_raw = goal.get("current")
        target_raw = goal.get("target")

        if current_raw is None or target_raw is None:
            return None, make_error_response(
                f"Goal at index {idx} is missing 'current' or 'target'."
            )

        current, err_c = to_float(current_raw)
        if err_c is not None:
            return None, make_error_response(
                f"Goal at index {idx} has invalid 'current': {err_c}"
            )

        target, err_t = to_float(target_raw)
        if err_t is not None:
            return None, make_error_response(
                f"Goal at index {idx} has invalid 'target': {err_t}"
            )

        base = compute_progress(current, target)
        # Attach id/label if present
        if "id" in goal:
            base["id"] = goal["id"]
        if "label" in goal:
            base["label"] = goal["label"]

        summaries.append(base)

    return summaries, None


# =========================
# Request / Response helpers
# =========================

def make_error_response(message):
    return {
        "status": "error",
        "error": message
    }


def make_success_response(mode, single_goal, goals_summary):
    """
    Standard success response.
    Always include 'single_goal' and 'goals_summary' keys
    for a stable schema.
    """
    return {
        "status": "ok",
        "mode": mode,
        "single_goal": single_goal,
        "goals_summary": goals_summary
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

    Returns:
      (mode, current, target, goals, error_or_None)
    """
    if request.get("request_type") != "progress_goal":
        return None, None, None, None, make_error_response(
            "Unsupported request_type. Expected 'progress_goal'."
        )

    mode = request.get("mode", "single")
    if mode not in ("single", "multi", "both"):
        return None, None, None, None, make_error_response(
            "Invalid 'mode'. Expected 'single', 'multi', or 'both'."
        )

    current = request.get("current")
    target = request.get("target")
    goals = request.get("goals")

    # For modes involving single, require current/target
    if mode in ("single", "both"):
        if current is None or target is None:
            return None, None, None, None, make_error_response(
                "'current' and 'target' are required for 'single' or 'both' modes."
            )

    # For modes involving multi, require goals list
    if mode in ("multi", "both"):
        if not isinstance(goals, list):
            return None, None, None, None, make_error_response(
                "'goals' must be a list for 'multi' or 'both' modes."
            )

    return mode, current, target, goals, None


def handle_message(raw_bytes):
    """
    Pure handler: bytes in → bytes out.
    Great for quick testing.
    """
    request, parse_error = parse_request_bytes(raw_bytes)
    if parse_error is not None:
        return serialize_response(parse_error)

    mode, current_raw, target_raw, goals, validation_error = validate_request(request)
    if validation_error is not None:
        return serialize_response(validation_error)

    single_goal_result = None
    multi_goals_result = []

    # Single-goal part
    if mode in ("single", "both"):
        single_goal_result, single_err = compute_single_goal(current_raw, target_raw)
        if single_err is not None:
            return serialize_response(single_err)

    # Multi-goal part
    if mode in ("multi", "both"):
        multi_goals_result, multi_err = compute_multi_goals(goals)
        if multi_err is not None:
            return serialize_response(multi_err)

    response = make_success_response(
        mode=mode,
        single_goal=single_goal_result,
        goals_summary=multi_goals_result
    )
    return serialize_response(response)


# =========================
# ZeroMQ server
# =========================

def create_socket(port):
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind(f"tcp://*:{port}")
    return context, socket


def run_server(port="5564"):
    """
    Main server loop.
    """
    context, socket = create_socket(port)
    print(f"[progress-goal] Listening on port {port}...", file=sys.stderr)

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
        print("\n[progress-goal] Interrupted via keyboard.", file=sys.stderr)
    finally:
        socket.close()
        context.term()


def main():
    port = os.getenv("PROGRESS_GOAL_PORT", "5564")
    run_server(port)


if __name__ == "__main__":
    main()
