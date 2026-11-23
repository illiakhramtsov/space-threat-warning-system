#!/usr/bin/env bash
set -e

HOST="${1:-http://localhost:8000}"
USERS="${2:-100}"
SPAWN_RATE="${3:-10}"
DURATION="${4:-1m}"
OUT_DIR="load_tests/results"

mkdir -p "$OUT_DIR"

echo "Running Locust against $HOST ($USERS VUsers, ramp-up $SPAWN_RATE/s, duration $DURATION)..."
locust -f load_tests/locustfile.py   --headless   --host "$HOST"   -u "$USERS"   -r "$SPAWN_RATE"   -t "$DURATION"   --csv "$OUT_DIR/run"   --html "$OUT_DIR/report.html"

python load_tests/plot_results.py --csv-prefix "$OUT_DIR/run" --out-dir "$OUT_DIR"
echo "Done! See $OUT_DIR/report.html and PNG charts in $OUT_DIR/"
