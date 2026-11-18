#!/bin/bash
# Smoke: the release binary launches, opens its window and quits cleanly (APP_SMOKE=1 exits after 2 s).
set -euo pipefail
cd "$(dirname "$0")/.."
swift build -c release >/dev/null
BIN="$(swift build -c release --show-bin-path)/__TARGET__"
APP_SMOKE=1 "$BIN" >/dev/null 2>&1 &
PID=$!
for _ in $(seq 1 30); do
  if ! kill -0 "$PID" 2>/dev/null; then
    wait "$PID" && { echo "smoke: launched and quit cleanly"; exit 0; }
    echo "smoke: exited with an error" >&2; exit 1
  fi
  sleep 0.5
done
kill "$PID" 2>/dev/null || true
echo "smoke: did not quit within 15 s" >&2
exit 1
