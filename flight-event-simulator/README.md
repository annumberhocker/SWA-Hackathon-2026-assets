# Flight Event Simulator

Produces a continuous stream of simulated flight schedule metrics to a Confluent Cloud Kafka topic (`flight-events`). Every 2 seconds it emits events for 4 aircraft across 3 metrics: `departure_delay`, `gate_wait`, and `turnaround_time`.

## Files

| File | Purpose |
|---|---|
| `flight_producer.py` | Main producer — runs the Kafka publish loop |
| `config.py` | Reads credentials from `.env` and defines fleet/topic constants |
| `env.example` | Template for your `.env` credentials file |
| `flink/add_watermarks.sql` | Flink SQL — adds event-time column and watermark to `flight-events` |

## Prerequisites

- Python 3.9+
- A Confluent Cloud cluster with the `flight-events` topic created
- A cluster-scoped Kafka API key and a Schema Registry API key

## Setup

### 1. Clone / navigate to this directory

```bash
cd flight-event-simulator
```

### 2. Configure your credentials

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

### 3. Create the Kafka topic (if it doesn't exist)

**Option A — Confluent CLI:**

Log in to the Confluent CLI (add `--save` to persist credentials):

```bash
confluent login --save
```

Set your default environment and cluster so you don't need to pass `--cluster` on every command:

```bash
confluent environment use <ENV_ID>
confluent kafka cluster use <CLUSTER_ID>
```

Replace `<ENV_ID>` and `<CLUSTER_ID>` with your values (e.g. `env-abc123` and `lkc-abc123`), which you can find under **Confluent Cloud → your cluster → Cluster Settings**.

Then create the topic:

```bash
confluent kafka topic create flight-events --partitions 3
```

**Option B — Confluent Cloud UI:**

1. Go to [confluent.cloud](https://confluent.cloud) and open your environment.
2. Select your Kafka cluster.
3. In the left navigation, click **Topics**.
4. Click **Add topic**.
5. Enter `flight-events` as the topic name.
6. Set **Partitions** to `3`.
7. Click **Create with defaults** (or adjust retention/cleanup settings as needed).

## Running the Producer

### 1. Create a virtual environment and install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Start the producer

```bash
python flight_producer.py
```

You should see output like:

```
Gate Change Cascade producer ready. Topic: flight-events. Starts emitting when state['running'] is True.
```

Events will be produced every 2 seconds. Press **Ctrl+C** to stop gracefully.

---

## Flink Watermarks

Before running Flink SQL queries that use event-time windows or joins over `flight-events`, you must add an `event_time` column and a watermark strategy. The SQL is in [`flink/add_watermarks.sql`](flink/add_watermarks.sql).

### Prerequisites

- The `flight_producer.py` simulator must be **running and producing messages** before you execute these statements. Confluent Cloud Flink infers the table schema from the live Schema Registry; if no messages have been published the table will appear with only raw `BYTES` columns.
- You need a Flink compute pool in the same Confluent Cloud environment as the `flight-events` topic.

### Steps

Open the Flink SQL workspace in the Confluent Cloud UI (**Flink** → your compute pool → **New statement**).

> ⚠️ Confluent Cloud Flink accepts **one statement per Run click**. Execute Step 1 and Step 2 separately, waiting for each to reach **COMPLETED** status before continuing.

#### Verify schema is available

Run this first to confirm the table columns are inferred (not raw `BYTES`):

```sql
DESCRIBE `flight-events`;
```

Expected output includes typed columns such as `flight_number STRING`, `aircraft_id STRING`, `metric STRING`, `value DOUBLE`, `hub STRING`, etc. If you only see `BYTES`, wait 10 seconds for the producer to publish and retry.

#### Step 1 — Add the event_time column

```sql
ALTER TABLE `flight-events`
    ADD event_time AS `$rowtime`;
```

Wait for status **COMPLETED**. If this fails with a column-already-exists error, skip to Step 2.

#### Step 2 — Attach the watermark

```sql
ALTER TABLE `flight-events`
    MODIFY WATERMARK FOR event_time AS event_time - INTERVAL '2' SECOND;
```

The 2-second lag tolerates minor out-of-order delivery from the simulator.

#### Verify

After both steps complete, run `DESCRIBE` again and confirm an `event_time` column with a `WATERMARK` annotation appears in the output:

```sql
DESCRIBE `flight-events`;
```

You should now see a row similar to:

```
event_time    TIMESTAMP_LTZ(3) *ROWTIME*    AS `$rowtime`    WATERMARK FOR event_time AS event_time - INTERVAL '2' SECOND
```

The topic is now ready for event-time Flink queries such as tumbling-window delay aggregations per hub or per-aircraft anomaly detection over `departure_delay`, `gate_wait`, and `turnaround_time`.

---

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
