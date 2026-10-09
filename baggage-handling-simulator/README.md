# Baggage Handling System Simulator

Produces a continuous stream of simulated baggage handling events and operational KPI metrics to a Confluent Cloud Kafka topic (`baggage-events`). Every 2 seconds it emits **two message shapes per flight**:

1. **Discrete tracking events** — a randomly sampled `event_type` (e.g. `checked_in`, `loaded_to_aircraft`, `misrouted`) with a synthetic bag ID and passenger ID.
2. **Continuous KPI metrics** — numeric operational measurements (e.g. `loading_time_minutes`, `carousel_wait_minutes`) with Gaussian noise and correlated drift.

## Files

| File | Purpose |
|---|---|
| `baggage_producer.py` | Main producer — runs the Kafka publish loop |
| `config.py` | Reads credentials from `.env` and defines fleet/topic/event constants |
| `env.example` | Template for your `.env` credentials file |

## Prerequisites

- Python 3.9+
- A Confluent Cloud cluster with the `baggage-events` topic created
- A cluster-scoped Kafka API key and a Schema Registry API key

## Setup

### 1. Navigate to this directory

```bash
cd baggage-handling-simulator
```

### 2. Configure your credentials

```bash
cp env.example .env
```

Open `.env` and replace every `<placeholder>` with real values:

```
BOOTSTRAP_SERVERS=pkc-xxxxx.us-east-2.aws.confluent.cloud:9092
KAFKA_API_KEY=YOUR_KAFKA_API_KEY
KAFKA_API_SECRET=YOUR_KAFKA_API_SECRET
SCHEMA_REGISTRY_ENDPOINT=https://psrc-xxxxx.us-east-2.aws.confluent.cloud
SCHEMA_REGISTRY_API_KEY=YOUR_SR_API_KEY
SCHEMA_REGISTRY_API_SECRET=YOUR_SR_API_SECRET
```

> **Note:** The Kafka API key must be **cluster-scoped**, not a Global API key.

### 3. Create the Kafka topic (if it doesn't exist)

**Option A — Confluent CLI:**

```bash
confluent login --save
confluent environment use <ENV_ID>
confluent kafka cluster use <CLUSTER_ID>
confluent kafka topic create baggage-events --partitions 3
```

**Option B — Confluent Cloud UI:**

1. Go to [confluent.cloud](https://confluent.cloud) and open your environment.
2. Select your Kafka cluster → **Topics** → **Add topic**.
3. Enter `baggage-events`, set **Partitions** to `3`, click **Create with defaults**.

### 4. Create a virtual environment and install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 5. Start the producer

```bash
python baggage_producer.py
```

Events will be produced every 2 seconds. Press **Ctrl+C** to stop gracefully.

---

## What Gets Produced

All messages are published to the `baggage-events` topic **keyed by `flight_number`**, serialized as JSON via the Schema Registry.

### Discrete tracking event (event_type ≠ `kpi_metric`)

```json
{
  "bag_id":        "BAG-A3F9C012",
  "flight_number": "AX101",
  "aircraft_id":   "N101AX",
  "origin":        "ORD",
  "destination":   "LAX",
  "terminal":      "T2",
  "event_type":    "loaded_to_aircraft",
  "metric":        null,
  "value":         null,
  "unit":          null,
  "passenger_id":  "PAX-8B2E1A",
  "timestamp":     "2025-07-14 18:42:01.123"
}
```

### KPI metric message (event_type = `kpi_metric`)

```json
{
  "bag_id":        "KPI",
  "flight_number": "AX101",
  "aircraft_id":   "N101AX",
  "origin":        "ORD",
  "destination":   "LAX",
  "terminal":      "T3",
  "event_type":    "kpi_metric",
  "metric":        "loading_time_minutes",
  "value":         29.41,
  "unit":          "minutes",
  "passenger_id":  "SYSTEM",
  "timestamp":     "2025-07-14 18:42:01.123"
}
```

---

## Event Types

| event_type | Category | Description |
|---|---|---|
| `checked_in` | Normal | Bag accepted at check-in counter |
| `security_cleared` | Normal | Bag passed TSA / security screening |
| `loaded_to_aircraft` | Normal | Bag placed in aircraft hold |
| `in_transit` | Normal | Bag scanned at connection point |
| `arrived_at_carousel` | Normal | Bag appeared on baggage claim carousel |
| `carousel_timeout` | Anomaly | Bag sitting on carousel too long — owner may not have collected |
| `misrouted` | Anomaly | Bag sent to incorrect destination |
| `delayed_loading` | Anomaly | Bag not loaded before aircraft departure |
| `damage_reported` | Anomaly | Bag or contents reported damaged |
| `lost` | Anomaly | Bag tracking signal lost entirely |

Anomaly events are emitted at low probability (weighted sampling). Higher-weight normal events dominate the stream, reflecting real-world baggage handling where the vast majority of bags are processed without incident.

---

## KPI Metrics

| Metric | Baseline | Std Dev | Unit |
|---|---|---|---|
| `loading_time_minutes`  | 28 min  | ±5 min  | minutes |
| `transfer_time_minutes` | 35 min  | ±8 min  | minutes |
| `carousel_wait_minutes` | 12 min  | ±4 min  | minutes |
| `bags_per_flight`       | 95 bags | ±15     | count   |
| `mishandling_rate_pct`  | 0.5%    | ±0.3%   | percent |

Each metric uses Gaussian noise with a slow mean-reverting drift term (autocorrelation ~0.99 per tick) to produce realistic, non-i.i.d. time series suitable for anomaly detection demos.

---

## Anomaly Injection

Drop a JSON file at `/tmp/bhs_anomaly.json` to spike a metric for a specific flight:

```json
[
  {
    "entity_id":  "AX101",
    "stream":     "baggage_ops",
    "metric":     "loading_time_minutes",
    "start_time": 1720000000.0,
    "intensity":  4.0
  }
]
```

| Field | Description |
|---|---|
| `entity_id` | Flight number (e.g. `AX101`) |
| `stream` | Always `baggage_ops` for KPI metrics |
| `metric` | One of the metric names in the KPI table above |
| `start_time` | Unix timestamp when the anomaly begins (`time.time()`) |
| `intensity` | Multiplier on the metric's standard deviation (1 = subtle, 5 = severe) |

The producer ramps the offset up over 20 s, holds it, then ramps it back down. The file is deleted automatically when all targets expire.

---

## Simulated Flights

| Flight | Aircraft | Route |
|---|---|---|
| AX101 | N101AX | ORD → LAX |
| AX202 | N202AX | ORD → JFK |
| AX303 | N303AX | DFW → MIA |
| AX404 | N404AX | DFW → SEA |

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Confluent authentication failed` | Verify `KAFKA_API_KEY` / `KAFKA_API_SECRET` are cluster-scoped |
| Schema Registry errors | Check `SCHEMA_REGISTRY_ENDPOINT`, `SCHEMA_REGISTRY_API_KEY`, `SCHEMA_REGISTRY_API_SECRET` |
| No messages appearing | Confirm the `baggage-events` topic exists in your cluster |
