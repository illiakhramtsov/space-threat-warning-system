"""Lab 6 verification script: sends N requests via Nginx and prints server distribution."""

import argparse
import urllib.request
from collections import Counter


def main() -> None:
    parser = argparse.ArgumentParser(description="Test Nginx Load Balancer distribution")
    parser.add_argument("--url", default="http://localhost:80/health")
    parser.add_argument("--requests", type=int, default=18)
    args = parser.parse_args()

    counts: Counter[str] = Counter()
    print(f"Sending {args.requests} sequential requests to {args.url}\n")
    for idx in range(1, args.requests + 1):
        try:
            with urllib.request.urlopen(args.url, timeout=3) as resp:
                server_id = resp.headers.get("X-Server-ID", "unknown")
                counts[server_id] += 1
                print(f"Request #{idx:02d} -> HTTP {resp.status} | X-Server-ID: {server_id}")
        except Exception as exc:
            counts["ERROR"] += 1
            print(f"Request #{idx:02d} -> FAILED ({exc})")

    print("\n--- Distribution Summary ---")
    for server, count in sorted(counts.items()):
        print(f"  {server}: {count} requests")


if __name__ == "__main__":
    main()
