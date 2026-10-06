# Flight Event Simulator

Produces a continuous stream of simulated flight schedule metrics to a Confluent Cloud Kafka topic (`flight-events`). Every 2 seconds it emits events for 4 aircraft across 3 metrics: `departure_delay`, `gate_wait`, and `turnaround_time`.

## Files

| File | Purpose |
|---|---|
| `flight_producer.py` | Main producer — runs the Kafka publish loop |
| `config.py` | Reads credentials from `.env` and defines fleet/topic constants |
| `env.example` | Template for your `.env` credentials file |

## Prerequisites

- Python 3.9+
- A Confluent Cloud cluster with the `flight-events` topic created
- A cluster-scoped Kafka API key and a Schema Registry API key

## Setup

### 1. Clone / navigate to this directory

```bash
cd flight-event-simulator
```

### 2. Create a virtual environment and install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install confluent-kafka python-dotenv
```

### 3. Configure your credentials

Copy the example env file and fill in your Confluent Cloud values:

```bash
cp env.example .env
```

Open `.env` in your editor and replace every `<placeholder>` with real values:

```
# Kafka bootstrap server — found under: Cluster → Cluster Settings → Endpoints
BOOTSTRAP_SERVERS=pkc-xxxxx.us-east-2.aws.confluent.cloud:9092

# Cluster-scoped API key — Confluent Cloud → your cluster → API keys → Add key
KAFKA_API_KEY=YOUR_KAFKA_API_KEY
KAFKA_API_SECRET=YOUR_KAFKA_API_SECRET

# Schema Registry — Confluent Cloud → your environment → Schema Registry
SCHEMA_REGISTRY_ENDPOINT=https://psrc-xxxxx.us-east-2.aws.confluent.cloud
SCHEMA_REGISTRY_API_KEY=YOUR_SR_API_KEY
SCHEMA_REGISTRY_API_SECRET=YOUR_SR_API_SECRET
```

> **Note:** The Kafka API key must be **cluster-scoped**, not a Global API key.

### 4. Create the Kafka topic (if it doesn't exist)

In Confluent Cloud, create a topic named `flight-events` with your preferred partition count (3 is a reasonable default).

## Running the Producer

```bash
python flight_producer.py
```

You should see output like:

```
Gate Change Cascade producer ready. Topic: flight-events. Starts emitting when state['running'] is True.
```

Events will be produced every 2 seconds. Press **Ctrl+C** to stop gracefully.

## What Gets Produced

Each message is published to the `flight-events` topic keyed by `flight_number`, serialized as JSON via the Schema Registry.

**Example message:**

```json
{
  "flight_number": "AX101",
  "aircraft_id":   "N101AX",
  "origin":        "ORD",
  "destination":   "LAX",
  "metric":        "departure_delay",
  "value":         2.34,
  "unit":          "minutes",
  "hub":           "ORD",
  "timestamp":     "2025-07-14 18:42:01.123"
}
```

**Simulated flights:**

| Flight | Aircraft | Route |
|---|---|---|
| AX101 | N101AX (B737-800) | ORD → LAX |
| AX202 | N202AX (A320neo)  | ORD → JFK |
| AX303 | N303AX (B737-MAX) | DFW → MIA |
| AX404 | N404AX (A321XLR)  | DFW → SEA |

**Metrics per flight per tick:**

| Metric | Baseline | Std Dev | Unit |
|---|---|---|---|
| `departure_delay` | 0 min | ±4 min | minutes |
| `gate_wait`       | 5 min | ±2 min | minutes |
| `turnaround_time` | 45 min | ±5 min | minutes |

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Confluent authentication failed` | Verify `KAFKA_API_KEY` / `KAFKA_API_SECRET` are cluster-scoped |
| `Schema Registry` errors | Check `SCHEMA_REGISTRY_ENDPOINT`, `SCHEMA_REGISTRY_API_KEY`, and `SCHEMA_REGISTRY_API_SECRET` |
| No messages appearing | Confirm the `flight-events` topic exists in your cluster |
