"""Build the flight manifest SQLite database for the Gate Change Cascade demo.

Creates two tables:
  flights      — static flight/aircraft reference data
  gate_changes — synthetic 30-day gate change history per flight

Run from the manifest-bundle/ directory:
    python build_manifest_db.py
"""

import random
import sqlite3
from datetime import datetime, timedelta, timezone

import os as _os
DB_PATH = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "flight_manifest.sqlite")

FLIGHTS = [
    {"flight_number": "AX101", "aircraft_id": "N101AX", "origin": "ORD",
     "destination": "LAX", "aircraft_type": "B737-800", "hub": "ORD", "passenger_count": 162},
    {"flight_number": "AX202", "aircraft_id": "N202AX", "origin": "ORD",
     "destination": "JFK", "aircraft_type": "A320neo",  "hub": "ORD", "passenger_count": 150},
    {"flight_number": "AX303", "aircraft_id": "N303AX", "origin": "DFW",
     "destination": "MIA", "aircraft_type": "B737-MAX", "hub": "DFW", "passenger_count": 178},
    {"flight_number": "AX404", "aircraft_id": "N404AX", "origin": "DFW",
     "destination": "SEA", "aircraft_type": "A321XLR",  "hub": "DFW", "passenger_count": 192},
]

GATES_BY_HUB = {
    "ORD": ["B12", "B13", "C4", "C5"],
    "DFW": ["A22", "A23", "D8",  "D9"],
}

GATE_CHANGE_REASONS = [
    "Aircraft swap",
    "Late inbound aircraft",
    "Gate conflict with incoming international flight",
    "Equipment issue at original gate",
    "Weather diversion — gate reassignment",
    "Crew rest compliance",
    "Oversize baggage equipment required",
]


def build():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # ── flights ───────────────────────────────────────────────────────────────
    cur.execute("DROP TABLE IF EXISTS flights")
    cur.execute("""
        CREATE TABLE flights (
            flight_number   TEXT PRIMARY KEY,
            aircraft_id     TEXT NOT NULL,
            origin          TEXT NOT NULL,
            destination     TEXT NOT NULL,
            aircraft_type   TEXT NOT NULL,
            hub             TEXT NOT NULL,
            passenger_count INTEGER NOT NULL
        )
    """)
    cur.executemany(
        "INSERT INTO flights VALUES (:flight_number,:aircraft_id,:origin,:destination,"
        ":aircraft_type,:hub,:passenger_count)",
        FLIGHTS,
    )

    # ── gate_changes ──────────────────────────────────────────────────────────
    cur.execute("DROP TABLE IF EXISTS gate_changes")
    cur.execute("""
        CREATE TABLE gate_changes (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            flight_number   TEXT NOT NULL,
            changed_at      TEXT NOT NULL,
            from_gate       TEXT NOT NULL,
            to_gate         TEXT NOT NULL,
            reason          TEXT NOT NULL
        )
    """)

    rng = random.Random(42)  # deterministic seed for reproducibility
    now = datetime.now(timezone.utc)

    rows = []
    for flight in FLIGHTS:
        fn   = flight["flight_number"]
        hub  = flight["hub"]
        gates = GATES_BY_HUB[hub]

        # Seed ~15 gate changes spread over the last 30 days (normal cadence)
        for day_offset in range(30, 0, -2):
            if rng.random() > 0.55:
                continue
            base_ts = now - timedelta(days=day_offset, hours=rng.randint(4, 20))
            from_g  = rng.choice(gates)
            to_g    = rng.choice([g for g in gates if g != from_g])
            rows.append((fn, base_ts.isoformat(), from_g, to_g, rng.choice(GATE_CHANGE_REASONS)))

    cur.executemany(
        "INSERT INTO gate_changes (flight_number, changed_at, from_gate, to_gate, reason) "
        "VALUES (?, ?, ?, ?, ?)",
        rows,
    )

    conn.commit()
    conn.close()

    import os
    size = os.path.getsize(DB_PATH)
    print(f"Created {DB_PATH} ({size} bytes)")
    print(f"  flights table:      {len(FLIGHTS)} rows")
    print(f"  gate_changes table: {len(rows)} rows")


if __name__ == "__main__":
    build()
