#!/usr/bin/env bash
set -euo pipefail

PORT="${1:-}"

# If port is not provided as an argument, prompt the user
if [[ -z "$PORT" ]]; then
    read -rp "Enter port number: " PORT
fi

# Validate that PORT is a number between 1 and 65535
if ! [[ "$PORT" =~ ^[0-9]+$ ]] || [ "$PORT" -lt 1 ] || [ "$PORT" -gt 65535 ]; then
    echo "Error: '$PORT' is not a valid port number (1-65535)." >&2
    exit 1
fi

# Find PIDs listening on the specified port
PIDS=$(lsof -ti ":$PORT" 2>/dev/null || true)

if [[ -z "$PIDS" ]]; then
    echo "No process found listening on port $PORT."
    exit 0
fi

echo "Found process(es) listening on port $PORT:"
ps -f -p $PIDS

# Attempt graceful termination first (SIGTERM)
echo "Stopping process(es)..."
kill $PIDS 2>/dev/null || true

# Wait up to 3 seconds for process to exit
PIDS_REMAINING=""
for _ in {1..6}; do
    PIDS_REMAINING=$(lsof -ti ":$PORT" 2>/dev/null || true)
    if [[ -z "$PIDS_REMAINING" ]]; then
        break
    fi
    sleep 0.5
done

# If still running, force terminate (SIGKILL)
if [[ -n "$PIDS_REMAINING" ]]; then
    echo "Process(es) still running; forcing termination with SIGKILL..."
    kill -9 $PIDS_REMAINING 2>/dev/null || true
    sleep 0.5
fi

# Verify port is clear
if lsof -ti ":$PORT" >/dev/null 2>&1; then
    echo "Error: Failed to stop process(es) on port $PORT." >&2
    exit 1
else
    echo "Port $PORT is now free."
fi
