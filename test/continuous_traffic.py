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
    parser = argparse.ArgumentParser(description="Continuous variable-load traffic generator")
    parser.add_argument("--url", default="http://localhost:25001/ingest",
                        help="Producer endpoint URL")
    parser.add_argument("--interval", type=float, default=60,
                        help="Seconds between bursts (default: 60)")
    parser.add_argument("--min-per-burst", type=int, default=1,
                        help="Min events per burst (default: 1)")
    parser.add_argument("--max-per-burst", type=int, default=5,
                        help="Max events per burst (default: 5)")
    parser.add_argument("--users", type=int, default=10,
                        help="Number of simulated user IDs (default: 10)")
    args = parser.parse_args()

    users = [f"user_{i}" for i in range(args.users)]
    burst_count = 0

    print(f"Continuous traffic to {args.url}")
    print(f"  Burst every {args.interval}s — {args.min_per_burst}-{args.max_per_burst} events per burst")
    print(f"  User pool: {args.users} users")
    print()

    while True:
        batch = random.randint(args.min_per_burst, args.max_per_burst)
        sent = 0
        for _ in range(batch):
            event_type = random.choice(EVENT_TYPES)
            user_id = random.choice(users)
            status = send_event(args.url, event_type, user_id)
            if 200 <= status < 300:
                sent += 1
            else:
                print(f"  FAILED (HTTP {status})", file=sys.stderr)

        burst_count += 1
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        print(f"[{ts}] Burst #{burst_count}: sent {sent}/{batch} events")
        sys.stdout.flush()

        time.sleep(args.interval)


if __name__ == "__main__":
    main()
