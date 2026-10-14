"""Baggage Handling System Simulator — configuration.

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
BAGGAGE_EVENTS_TOPIC = "baggage-events"

# ── Airports / hubs ───────────────────────────────────────────────────────────
AIRPORTS = {
    "ORD": {"city": "Chicago",     "terminals": ["T1", "T2", "T3", "T5"]},
    "DFW": {"city": "Dallas",      "terminals": ["TA", "TB", "TC", "TD", "TE"]},
    "LAX": {"city": "Los Angeles", "terminals": ["T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8"]},
    "JFK": {"city": "New York",    "terminals": ["T1", "T2", "T4", "T5", "T7", "T8"]},
    "MIA": {"city": "Miami",       "terminals": ["TN", "TS", "TE"]},
    "SEA": {"city": "Seattle",     "terminals": ["TA", "TC"]},
}

# ── Flights that generate baggage events ─────────────────────────────────────
FLIGHTS = [
    {"flight_number": "AX101", "aircraft_id": "N101AX", "origin": "ORD", "destination": "LAX"},
    {"flight_number": "AX202", "aircraft_id": "N202AX", "origin": "ORD", "destination": "JFK"},
    {"flight_number": "AX303", "aircraft_id": "N303AX", "origin": "DFW", "destination": "MIA"},
    {"flight_number": "AX404", "aircraft_id": "N404AX", "origin": "DFW", "destination": "SEA"},
]

# ── Baggage event type probabilities ─────────────────────────────────────────
# (event_type, weight)  — weights are relative, not percentages
BAGGAGE_EVENT_TYPES = [
    ("checked_in",              30),
    ("security_cleared",        25),
    ("loaded_to_aircraft",      20),
    ("in_transit",              10),
    ("arrived_at_carousel",     20),
    ("carousel_timeout",         3),   # anomaly: bag sitting too long on carousel
    ("misrouted",                2),   # anomaly: sent to wrong destination
    ("delayed_loading",          4),   # anomaly: not loaded before departure
    ("damage_reported",          1),   # anomaly: bag reported damaged
    ("lost",                     1),   # anomaly: bag tracking lost
]

# ── Baggage metric profiles (numeric KPIs emitted continuously) ──────────────
# stream = 'baggage_ops'
BAGGAGE_METRIC_PROFILES = {
    "loading_time_minutes":   {"mean": 28.0, "std": 5.0,  "unit": "minutes"},
    "transfer_time_minutes":  {"mean": 35.0, "std": 8.0,  "unit": "minutes"},
    "carousel_wait_minutes":  {"mean": 12.0, "std": 4.0,  "unit": "minutes"},
    "bags_per_flight":        {"mean": 95.0, "std": 15.0, "unit": "count"},
    "mishandling_rate_pct":   {"mean": 0.5,  "std": 0.3,  "unit": "percent"},
}
