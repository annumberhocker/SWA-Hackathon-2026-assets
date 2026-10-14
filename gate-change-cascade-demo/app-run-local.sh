#!/usr/bin/env bash
# Start the Gate Change Cascade demo locally.
# Runs three background processes:
#   1. Flight producer  — writes to flight-events
#   2. Alert consumer   — reads ops-alerts, dispatches to WXO supervisor agent
#   3. Streamlit dashboard — http://localhost:8080
#
# Usage:
#   bash app-run-local.sh
#
# Stop with Ctrl+C — the trap cleans up all child processes.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ── Activate virtual environment if present ───────────────────────────────────
if [ -f ".venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi

PIDS=()

cleanup() {
    echo ""
    echo "Shutting down Gate Change Cascade demo..."
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    wait 2>/dev/null || true
    echo "Done."
}
trap cleanup EXIT INT TERM

# ── Control server (must start before producer so autostart flag is honored) ──
echo "Starting simulator control server..."
SIMULATOR_AUTOSTART=1 python -m simulator.control_server &
PIDS+=($!)
sleep 1

# ── Flight producer ───────────────────────────────────────────────────────────
echo "Starting flight events producer..."
python -m simulator.flight_producer &
PIDS+=($!)

# ── Alert consumer ────────────────────────────────────────────────────────────
echo "Starting ops-alerts consumer..."
python -m simulator.alert_consumer &
PIDS+=($!)

# ── Streamlit dashboard ───────────────────────────────────────────────────────
echo "Starting Streamlit dashboard on http://localhost:8080 ..."
streamlit run frontend/app.py \
    --server.port 8080 \
    --server.address 0.0.0.0 \
    --server.headless true \
    --server.runOnSave false \
    &
PIDS+=($!)

echo ""
echo "Gate Change Cascade demo running."
echo "  Dashboard:  http://localhost:8080"
echo "  Control:    http://localhost:8090/status"
echo ""
echo "Press Ctrl+C to stop all processes."

wait
