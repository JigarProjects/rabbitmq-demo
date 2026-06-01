import argparse
import json
import random
import sys
import time
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import URLError

EVENT_TYPES = ["page_view", "click", "purchase", "login", "logout", "signup", "error", "search"]


def send_event(url: str, event_type: str, user_id: str) -> int:
    payload = json.dumps({
        "event_type": event_type,
        "user_id": user_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {"value": random.randint(1, 1000)},
    }).encode()
    req = Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=5) as resp:
            return resp.status
    except URLError as e:
        print(f"  Error: {e}", file=sys.stderr)
        return 0


def main():
    parser = argparse.ArgumentParser(description="Send test events to the ingest endpoint")
    parser.add_argument("--url", default="http://localhost:25001/ingest",
                        help="Producer endpoint URL")
    parser.add_argument("--rate", type=float, default=1,
                        help="Events per second (default: 1)")
    parser.add_argument("--users", type=int, default=5,
                        help="Number of simulated user IDs (default: 5)")
    parser.add_argument("--count", type=int, default=0,
                        help="Total events to send (0 = unlimited)")
    args = parser.parse_args()

    users = [f"user_{i}" for i in range(args.users)]
    sent = 0
    interval = 1.0 / args.rate

    print(f"Sending to {args.url} at {args.rate} evt/s (users={args.users}, count={'unlimited' if args.count == 0 else args.count})")
    print()

    while args.count == 0 or sent < args.count:
        event_type = random.choice(EVENT_TYPES)
        user_id = random.choice(users)
        status = send_event(args.url, event_type, user_id)
        if 200 <= status < 300:
            sent += 1
            print(f"  [{sent}] {event_type} by {user_id}")
        else:
            print(f"  [{sent + 1}] {event_type} by {user_id} -> FAILED (HTTP {status})", file=sys.stderr)
        time.sleep(interval)

    print(f"\nDone. {sent} events sent.")


if __name__ == "__main__":
    main()
