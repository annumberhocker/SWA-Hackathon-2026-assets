"""Gate Change Cascade Simulator — flight-events producer.

Produces a single real-time stream to Confluent Kafka:
    flight-events   Schedule status per flight (departure_delay, gate_wait, turnaround_time)

Anomaly injection:
    Reads from /tmp/gcc_anomaly.json (written by anomaly_injector.py).
    Each target: {entity_id, stream, metric, start_time, intensity}
"""

import json
import os
import random
import time
from datetime import datetime, timezone

from confluent_kafka import Producer
from confluent_kafka.serialization import SerializationContext, MessageField
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.json_schema import JSONSerializer

from config import (
    KAFKA_CONFIG,
    SCHEMA_REGISTRY_CONFIG,
    FLIGHT_EVENTS_TOPIC,
    AIRCRAFT,
    FLIGHTS,
    SCHEDULE_PROFILES,
)

ANOMALY_FILE = "/tmp/gcc_anomaly.json"

# ── JSON Schema ───────────────────────────────────────────────────────────────

FLIGHT_SCHEMA_STR = json.dumps({
    "type": "object",
    "properties": {
        "flight_number":    {"type": "string"},
        "aircraft_id":      {"type": "string"},
        "origin":           {"type": "string"},
        "destination":      {"type": "string"},
        "metric":           {"type": "string"},
        "value":            {"type": "number"},
        "unit":             {"type": "string"},
        "hub":              {"type": "string"},
        "timestamp":        {"type": "string"},
    },
    "required": ["flight_number", "aircraft_id", "origin", "destination",
                 "metric", "value", "unit", "hub", "timestamp"],
})

RAMP_DURATION_S = 20.0
TUMBLE_WINDOW_S = 10.0


# ── Anomaly helpers ────────────────────────────────────────────────────────────

def load_anomaly_targets() -> list:
    if not os.path.exists(ANOMALY_FILE):
        return []
    try:
        with open(ANOMALY_FILE, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return []
    if isinstance(data, list):
        return [t for t in data if isinstance(t, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def _save_targets(targets: list) -> None:
    if not targets:
        try:
            os.remove(ANOMALY_FILE)
        except FileNotFoundError:
            pass
        return
    with open(ANOMALY_FILE, "w") as f:
        json.dump(targets, f)


def _expire_targets(targets: list) -> list:
    now = time.time()
    active, changed = [], False
    for t in targets:
        intensity = float(t.get("intensity", 3.0))
        ramp_down = t.get("ramp_down_s", 25.0)
        n = RAMP_DURATION_S + TUMBLE_WINDOW_S + max(20.0, 40.0 / intensity) + ramp_down
        if now - t.get("start_time", now) < n:
            active.append(t)
        else:
            changed = True
    if changed:
        _save_targets(active)
    return active


def compute_anomaly_offset(anomaly, profile):
    elapsed = time.time() - anomaly["start_time"]
    intensity = float(anomaly["intensity"])
    n = RAMP_DURATION_S + TUMBLE_WINDOW_S + max(20.0, 40.0 / intensity)
    ramp_down = anomaly.setdefault("ramp_down_s", random.uniform(15.0, 25.0))

    if elapsed <= RAMP_DURATION_S:
        ramp = elapsed / RAMP_DURATION_S
    elif elapsed <= n:
        ramp = 1.0
    elif elapsed <= n + ramp_down:
        ramp = 1.0 - (elapsed - n) / ramp_down
    else:
        ramp = 0.0

    return ramp * intensity * profile["std"]


def delivery_report(err, msg):
    if err is not None:
        print(f"Delivery failed for {msg.key()}: {err}")


def _to_dict(obj, ctx):
    return obj


def _now_ts():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


# ── Producer loop ──────────────────────────────────────────────────────────────

def _producer_loop(state):
    """Emit flight-events stream every 2 seconds."""
    sr_client = SchemaRegistryClient(SCHEMA_REGISTRY_CONFIG)
    flight_serializer = JSONSerializer(FLIGHT_SCHEMA_STR, sr_client, to_dict=_to_dict)
    producer = Producer(KAFKA_CONFIG)

    # Per-aircraft per-metric drift accumulator for realistic autocorrelation
    sched_drift = {(f["aircraft_id"], m): 0.0 for f in FLIGHTS for m in SCHEDULE_PROFILES}

    print(f"Gate Change Cascade producer ready. Topic: {FLIGHT_EVENTS_TOPIC}. "
          "Starts emitting when state['running'] is True.")

    while True:
        if not state.get("running"):
            time.sleep(1)
            continue

        targets = _expire_targets(load_anomaly_targets())
        targets_by_key = {
            (t.get("entity_id"), t.get("stream"), t.get("metric")): t
            for t in targets
        }

        ts = _now_ts()

        # ── Flight schedule events ─────────────────────────────────────────────
        for flight in FLIGHTS:
            aircraft_id   = flight["aircraft_id"]
            flight_number = flight["flight_number"]
            hub           = AIRCRAFT[aircraft_id]["hub"]

            for metric, profile in SCHEDULE_PROFILES.items():
                dk = (aircraft_id, metric)
                sched_drift[dk] = sched_drift.get(dk, 0.0) + random.gauss(0, profile["std"] * 0.01)
                sched_drift[dk] *= 0.99

                value = random.gauss(profile["mean"], profile["std"]) + sched_drift[dk]

                # Apply anomaly offset if injection is active for this flight/metric
                t = targets_by_key.get((flight_number, "schedule", metric))
                if t:
                    value += compute_anomaly_offset(t, profile)

                message = {
                    "flight_number": flight_number,
                    "aircraft_id":   aircraft_id,
                    "origin":        flight["origin"],
                    "destination":   flight["destination"],
                    "metric":        metric,
                    "value":         round(value, 2),
                    "unit":          profile["unit"],
                    "hub":           hub,
                    "timestamp":     ts,
                }
                try:
                    producer.produce(
                        FLIGHT_EVENTS_TOPIC,
                        key=flight_number,
                        value=flight_serializer(
                            message,
                            SerializationContext(FLIGHT_EVENTS_TOPIC, MessageField.VALUE),
                        ),
                        callback=delivery_report,
                    )
                    state["sent"] = state.get("sent", 0) + 1
                except Exception as exc:
                    state["errors"] = state.get("errors", 0) + 1
                    print(f"flight produce error: {exc}")

        producer.poll(0)
        time.sleep(2)


def run_with_state(state):
    try:
        _producer_loop(state)
    except KeyboardInterrupt:
        print("\nShutting down Gate Change Cascade producer...")


def run():
    state = {"running": True, "sent": 0, "errors": 0}
    try:
        _producer_loop(state)
    except KeyboardInterrupt:
        print("\nShutting down Gate Change Cascade producer...")


if __name__ == "__main__":
    run()
