# change: replaces long banner comment with short docstring
"""Microservice for calculating current and longest streaks from provided dates."""

# change: trimmed imports to only what is used
from datetime import date, datetime, timedelta
import sys
import threading
import zmq  # change: keep third-party import grouped for clarity

# change: keep supported formats compact to avoid long comment blocks
DATE_FORMATS = [
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%d-%b-%Y",
    "%b %d %Y",
]


def parse_date_string(raw: str):
    # change: short docstring replaces verbose comments
    """Try multiple formats; return date or None if all fail."""
    raw = raw.strip()  # change: clearer variable name to reduce vague naming
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _extract_date_strings(payload):
    # change: split validation to trim process_request length
    """Pull out date strings or return an error message."""
    if "dates" not in payload or not isinstance(payload["dates"], list):
        return [], "Request must contain a 'dates' array."  # change: isolates validation response
    date_strings = [value for value in payload["dates"] if isinstance(value, str)]
    return date_strings, None  # change: uniform tuple simplifies caller logic


def _parse_dates(date_strings):
    # change: dedicated parser avoids multi-job functions
    """Convert strings into parsed date objects."""
    parsed_dates = []
    for raw_date in date_strings:
        parsed_date = parse_date_string(raw_date)
        if parsed_date is not None:
            parsed_dates.append(parsed_date)
    return parsed_dates


def _count_forward_streak(dates_set, start_date):
    # change: helper shortens calculate_longest_streak
    """Count consecutive days forward from a start date."""
    length = 1
    curr = start_date
    while curr + timedelta(days=1) in dates_set:
        curr += timedelta(days=1)
        length += 1
    return length


def calculate_longest_streak(dates):
    """dates: set[date]"""
    if not dates:
        return 0
    dates_set = set(dates)
    longest = 0
    for current_date in dates_set:
        if current_date - timedelta(days=1) in dates_set:
            continue  # change: skip non-start days to avoid duplicate counting
        # change: reuse helper to avoid duplicating counting logic
        longest = max(longest, _count_forward_streak(dates_set, current_date))
    return longest


def _count_backward_streak(dates_set, start_date):
    # change: helper keeps calculate_current_streak focused
    """Count consecutive days backward from the given date."""
    length = 0
    curr = start_date
    while curr in dates_set:
        length += 1
        curr -= timedelta(days=1)
    return length


def calculate_current_streak(dates):
    """Current streak up to today's date."""
    if not dates:
        return 0
    today = date.today()
    dates_set = set(dates)
    if today not in dates_set:
        return 0  # change: guard clause keeps function short and clear
    # change: reuse helper to reduce duplication
    return 1 + _count_backward_streak(dates_set, today - timedelta(days=1))


def _error(message):
    """Return a consistent error payload."""  # change: helper removes duplicate literal dicts
    return {"ok": False, "error": message}


def process_request(payload: dict) -> dict:
    """
    payload: dict with key "dates": list[str]
    returns dict with ok/result or ok/error
    """
    if not isinstance(payload, dict):
        # change: type guard avoids attribute errors
        return _error("Request must contain a 'dates' array.")
    date_strings, error = _extract_date_strings(payload)
    if error:
        return _error(error)  # change: centralizes validation response
    parsed_dates = _parse_dates(date_strings)
    if not parsed_dates:
        # change: keeps existing error while using helper output
        return _error("No valid dates provided.")
    return {
        "ok": True,
        "result": {
            "current_streak": calculate_current_streak(parsed_dates),
            "longest_streak": calculate_longest_streak(parsed_dates),
        },
    }


def shutdown_listener(stop_flag):
    """
    Waits for the user to type 'q' then Enter to request shutdown.
    Sets stop_flag[0] = True so the main loop can exit cleanly.
    """
    print("Press 'q' then Enter to stop the microservice...")
    for line in sys.stdin:
        if line.strip().lower() == "q":
            stop_flag[0] = True
            print("Shutdown requested...")
            break


def start_shutdown_listener(stop_flag):
    # change: separates thread setup to shorten main
    """Start the background shutdown listener thread."""
    listener_thread = threading.Thread(
        target=shutdown_listener,
        args=(stop_flag,),
        daemon=True
    )
    listener_thread.start()
    return listener_thread  # change: return enables future callers to join if needed


def serve_requests(socket, stop_flag):
    # change: extracted loop to keep main single-purpose
    """Process inbound requests until stop_flag is set."""
    while not stop_flag[0]:
        if socket.poll(timeout=1000):
            payload = socket.recv_json()
            response = process_request(payload)
            socket.send_json(response)


def build_server_socket(port):
    # change: isolates socket setup for clarity
    """Create and bind the REP socket for the service."""
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    address = f"tcp://*:{port}"
    socket.bind(address)
    return context, socket, address  # change: returns address so caller can log consistently


def shutdown(context, socket):
    """Close resources cleanly."""  # change: shared cleanup prevents duplicate code paths
    print("Shutting down microservice...")
    socket.close()
    context.term()


def run_service(port):
    # change: keeps main tiny and readable
    """Start the microservice lifecycle for the given port."""
    context, socket, address = build_server_socket(port)
    print(f"Streaks microservice listening on {address}")
    stop_flag = [False]
    start_shutdown_listener(stop_flag)
    try:
        serve_requests(socket, stop_flag)
    except Exception as exc:
        print(f"Error in microservice: {exc}")  # change: keep error log without a long function
    finally:
        shutdown(context, socket)


def main(port=5555):
    run_service(port)
    sys.exit(0)  # change: explicit exit keeps CLI behavior unchanged


if __name__ == "__main__":
    port = 5555  # default port
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port '{sys.argv[1]}', using default 5555 instead.")
    main(port)
