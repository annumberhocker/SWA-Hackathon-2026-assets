#!/usr/bin/env bash
# Stop all processes started by app-run-local.sh.
# Use this when the original terminal is gone or when you want to stop
# the demo from a different shell. Ctrl+C in the original terminal also works.

set -uo pipefail

stopped=0

stop_procs() {
    local pattern="$1"
    local label="$2"
    local pids
    pids=$(pgrep -f "$pattern" 2>/dev/null) || true
    if [ -n "$pids" ]; then
        echo "  Stopping $label..."
        # shellcheck disable=SC2086
        kill $pids 2>/dev/null || true
        stopped=$((stopped + 1))
    fi
}

echo "Stopping Gate Change Cascade demo..."

stop_procs "simulator.control_server"  "simulator control server"
stop_procs "simulator.flight_producer" "flight events producer"
stop_procs "simulator.alert_consumer"  "ops-alerts consumer"
stop_procs "frontend/app.py"           "Streamlit dashboard"

if [ "$stopped" -eq 0 ]; then
    echo "  Nothing running."
else
    echo "Done."
fi
