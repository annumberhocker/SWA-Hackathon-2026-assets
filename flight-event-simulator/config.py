"""Flight Event Simulator — configuration.

Reads connection details from a .env file in the same directory as this script.
Copy env.example to .env and fill in your Confluent Cloud credentials.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the same directory as this file
_ENV = Path(__file__).resolve().parent / ".env"
load_dotenv(_ENV)

_auth_error_shown = False


def kafka_error_cb(err):
    """Suppress raw rdkafka log spam; print one clean message on auth failure."""
    global _auth_error_shown
    from confluent_kafka import KafkaError
    if err.code() == KafkaError._AUTHENTICATION and not _auth_error_shown:
        _auth_error_shown = True
        print(
            "\n[error] Confluent authentication failed.\n"
            "        Check KAFKA_API_KEY and KAFKA_API_SECRET in .env\n"
            "        The key must be cluster-scoped (not Global) in Confluent Cloud.\n"
        )


KAFKA_CONFIG = {
    "bootstrap.servers": os.getenv("BOOTSTRAP_SERVERS"),
    "security.protocol": "SASL_SSL",
    "sasl.mechanisms": "PLAIN",
    "sasl.username": os.getenv("KAFKA_API_KEY"),
    "sasl.password": os.getenv("KAFKA_API_SECRET"),
    "log_level": 0,
    "error_cb": kafka_error_cb,
}

SCHEMA_REGISTRY_CONFIG = {
    "url": os.getenv("SCHEMA_REGISTRY_ENDPOINT"),
    "basic.auth.user.info": "{}:{}".format(
        os.getenv("SCHEMA_REGISTRY_API_KEY", ""),
        os.getenv("SCHEMA_REGISTRY_API_SECRET", ""),
    ),
}

# ── Topic names ───────────────────────────────────────────────────────────────
FLIGHT_EVENTS_TOPIC = "flight-events"

# ── Fleet ─────────────────────────────────────────────────────────────────────
# aircraft_id → {tail, type, hub, criticality}
AIRCRAFT = {
    "N101AX": {"tail": "N101AX", "type": "B737-800", "hub": "ORD", "criticality": "high"},
    "N202AX": {"tail": "N202AX", "type": "A320neo",  "hub": "ORD", "criticality": "medium"},
    "N303AX": {"tail": "N303AX", "type": "B737-MAX", "hub": "DFW", "criticality": "high"},
    "N404AX": {"tail": "N404AX", "type": "A321XLR",  "hub": "DFW", "criticality": "critical"},
}

# ── Flight schedule (static rotation for the demo) ───────────────────────────
FLIGHTS = [
    {"aircraft_id": "N101AX", "flight_number": "AX101", "origin": "ORD", "destination": "LAX"},
    {"aircraft_id": "N202AX", "flight_number": "AX202", "origin": "ORD", "destination": "JFK"},
    {"aircraft_id": "N303AX", "flight_number": "AX303", "origin": "DFW", "destination": "MIA"},
    {"aircraft_id": "N404AX", "flight_number": "AX404", "origin": "DFW", "destination": "SEA"},
]

# ── Flight schedule metric profiles ──────────────────────────────────────────
# stream = 'schedule'
SCHEDULE_PROFILES = {
    "departure_delay": {"mean": 0.0,  "std": 4.0, "unit": "minutes"},
    "gate_wait":       {"mean": 5.0,  "std": 2.0, "unit": "minutes"},
    "turnaround_time": {"mean": 45.0, "std": 5.0, "unit": "minutes"},
}
