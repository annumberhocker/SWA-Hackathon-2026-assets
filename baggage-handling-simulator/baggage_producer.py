"""Baggage Handling System Simulator — baggage-events producer.

Produces a single real-time stream to Confluent Kafka:
    baggage-events   Baggage tracking events and operational KPI metrics per flight

Two message shapes are emitted on every tick:
  1. Discrete event messages  — randomly sampled event_type (checked_in, loaded,
     misrouted, lost, …) for individual bag IDs.
  2. Continuous metric messages — numeric KPIs (loading_time, carousel_wait, …)
     with Gaussian noise and drift, matching the flight-event-simulator pattern.

Anomaly injection:
    Reads from /tmp/bhs_anomaly.json (written externally).
    Each target: {entity_id, stream, metric, start_time, intensity}
"""

import json
import os
import random
import time
import uuid
from datetime import datetime, timezone

from confluent_kafka import Producer
from confluent_kafka.serialization import SerializationContext, MessageField
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.json_schema import JSONSerializer

from config import (
    KAFKA_CONFIG,
    SCHEMA_REGISTRY_CONFIG,
    BAGGAGE_EVENTS_TOPIC,
    AIRPORTS,
    FLIGHTS,
    BAGGAGE_EVENT_TYPES,
    BAGGAGE_METRIC_PROFILES,
)

ANOMALY_FILE = "/tmp/bhs_anomaly.json"

# ── JSON Schema ───────────────────────────────────────────────────────────────

BAGGAGE_SCHEMA_STR = json.dumps({
    "type": "object",
    "properties": {
        "bag_id":         {"type": "string"},
        "flight_number":  {"type": "string"},
        "aircraft_id":    {"type": "string"},
        "origin":         {"type": "string"},
        "destination":    {"type": "string"},
        "terminal":       {"type": "string"},
        "event_type":     {"type": "string"},
        "metric":         {"type": ["string", "null"]},
        "value":          {"type": ["number", "null"]},
        "unit":           {"type": ["string", "null"]},
        "passenger_id":   {"type": "string"},
        "timestamp":      {"type": "string"},
    },
    "required": [
        "bag_id", "flight_number", "aircraft_id",
        "origin", "destination", "terminal",
        "event_type", "metric", "value", "unit",
        "passenger_id", "timestamp",
    ],
})

RAMP_DURATION_S = 20.0
TUMBLE_WINDOW_S = 10.0

# ── Weighted event-type sampler ───────────────────────────────────────────────
_EVENT_POPULATION = [et for et, w in BAGGAGE_EVENT_TYPES for _ in range(w)]


def _sample_event_type() -> str:
    return random.choice(_EVENT_POPULATION)


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
    else:
        print(f"✓ [{msg.topic()}] key={msg.key().decode()} partition={msg.partition()} offset={msg.offset()}")


def _to_dict(obj, ctx):
    return obj


def _now_ts():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


# ── Producer loop ──────────────────────────────────────────────────────────────

def _producer_loop(state):
    """Emit baggage-events stream every 2 seconds."""
    sr_client = SchemaRegistryClient(SCHEMA_REGISTRY_CONFIG)
    baggage_serializer = JSONSerializer(BAGGAGE_SCHEMA_STR, sr_client, to_dict=_to_dict)
    producer = Producer(KAFKA_CONFIG)

    # Per-flight per-metric drift accumulator for realistic autocorrelation
    metric_drift = {(f["flight_number"], m): 0.0 for f in FLIGHTS for m in BAGGAGE_METRIC_PROFILES}

    print(f"Baggage Handling System producer ready. Topic: {BAGGAGE_EVENTS_TOPIC}. "
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

        for flight in FLIGHTS:
            flight_number = flight["flight_number"]
            aircraft_id   = flight["aircraft_id"]
            origin        = flight["origin"]
            destination   = flight["destination"]

            origin_terminals      = AIRPORTS[origin]["terminals"]
            destination_terminals = AIRPORTS[destination]["terminals"]

            # ── 1. Discrete baggage tracking event ────────────────────────────
            event_type = _sample_event_type()
            # Pick terminal: loading/check-in events at origin; arrival events at destination
            if event_type in ("checked_in", "security_cleared", "loaded_to_aircraft",
                              "delayed_loading", "damage_reported"):
                terminal = random.choice(origin_terminals)
            else:
                terminal = random.choice(destination_terminals)

            bag_id       = "BAG-" + uuid.uuid4().hex[:8].upper()
            passenger_id = "PAX-" + uuid.uuid4().hex[:6].upper()

            discrete_msg = {
                "bag_id":        bag_id,
                "flight_number": flight_number,
                "aircraft_id":   aircraft_id,
                "origin":        origin,
                "destination":   destination,
                "terminal":      terminal,
                "event_type":    event_type,
                "metric":        None,
                "value":         None,
                "unit":          None,
                "passenger_id":  passenger_id,
                "timestamp":     ts,
            }
            try:
                producer.produce(
                    BAGGAGE_EVENTS_TOPIC,
                    key=flight_number,
                    value=baggage_serializer(
                        discrete_msg,
                        SerializationContext(BAGGAGE_EVENTS_TOPIC, MessageField.VALUE),
                    ),
                    callback=delivery_report,
                )
                state["sent"] = state.get("sent", 0) + 1
            except Exception as exc:
                state["errors"] = state.get("errors", 0) + 1
                print(f"baggage discrete produce error: {exc}")

            # ── 2. Continuous KPI metric events ───────────────────────────────
            for metric, profile in BAGGAGE_METRIC_PROFILES.items():
                dk = (flight_number, metric)
                metric_drift[dk] = metric_drift.get(dk, 0.0) + random.gauss(0, profile["std"] * 0.01)
                metric_drift[dk] *= 0.99

                value = random.gauss(profile["mean"], profile["std"]) + metric_drift[dk]
                value = max(0.0, value)  # KPIs are non-negative

                # Apply anomaly offset if injection is active for this flight/metric
                t = targets_by_key.get((flight_number, "baggage_ops", metric))
                if t:
                    value += compute_anomaly_offset(t, profile)

                kpi_msg = {
                    "bag_id":        "KPI",
                    "flight_number": flight_number,
                    "aircraft_id":   aircraft_id,
                    "origin":        origin,
                    "destination":   destination,
                    "terminal":      random.choice(origin_terminals),
                    "event_type":    "kpi_metric",
                    "metric":        metric,
                    "value":         round(value, 2),
                    "unit":          profile["unit"],
                    "passenger_id":  "SYSTEM",
                    "timestamp":     ts,
                }
                try:
                    producer.produce(
                        BAGGAGE_EVENTS_TOPIC,
                        key=flight_number,
                        value=baggage_serializer(
                            kpi_msg,
                            SerializationContext(BAGGAGE_EVENTS_TOPIC, MessageField.VALUE),
                        ),
                        callback=delivery_report,
                    )
                    state["sent"] = state.get("sent", 0) + 1
                except Exception as exc:
                    state["errors"] = state.get("errors", 0) + 1
                    print(f"baggage kpi produce error: {exc}")

        producer.poll(0)
        time.sleep(2)


def run_with_state(state):
    try:
        _producer_loop(state)
    except KeyboardInterrupt:
        print("\nShutting down Baggage Handling System producer...")


def run():
    state = {"running": True, "sent": 0, "errors": 0}
    try:
        _producer_loop(state)
    except KeyboardInterrupt:
        print("\nShutting down Baggage Handling System producer...")


if __name__ == "__main__":
    run()
