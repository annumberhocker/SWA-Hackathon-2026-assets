#!/usr/bin/env bash
# Build the flight manifest SQLite database.
# Run from the manifest-bundle/ directory or the orchestrate/ root.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if command -v python3 &>/dev/null; then
    python3 build_manifest_db.py
else
    python build_manifest_db.py
fi
