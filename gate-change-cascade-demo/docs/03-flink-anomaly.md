# Doc 03 — Flink SQL Anomaly Detection

**Gate Change Cascade Demo — Step 3**

---

This step deploys three Flink SQL statements that turn the raw `flight-events` stream into a continuous anomaly detection pipeline. Event-time watermarks are added first so that Flink can reason about out-of-order events; an output table is then created to receive scored alerts; and finally a long-running streaming job uses Confluent's built-in `AI_DETECT_ANOMALIES` function to score each 10-second tumbling window against a statistical model. Any window whose anomaly score exceeds 0.95 is written to the `ops-alerts-ai` topic and can be consumed downstream by watsonx agents or dashboards in real time.

---

## Overview

Three Flink SQL statements run in order:

| File | What it does | Run once or continuously |
|---|---|---|
| `flink/01_add_watermarks.sql` | Adds event-time watermark to `flight-events` | Run once |
| `flink/02_alerts_table.sql` | Creates the `ops-alerts` output table | Run once |
| `flink/03_anomaly_detection_ai.sql` | Continuous `AI_DETECT_ANOMALIES` INSERT | Runs continuously |

> ⚠️ **Prerequisite:** The simulator must be running AND have published at least one message to `flight-events` before running statement 01. Flink needs the schema in Schema Registry to parse the table columns.

---

## Step 3.1 — Add Watermarks

Run each statement in `flink/01_add_watermarks.sql` **one at a time**.

### Using Bob

```
Run each SQL statement from flink/01_add_watermarks.sql
one at a time.
```

```text
mcp__confluent__create-flink-statement
  {
    "statementName": "gcc-watermark-event-time",
    "catalogName":   "<environment-name>",
    "databaseName":  "<cluster-name>",
    "computePoolId": "<FLINK_COMPUTE_POOL_ID>",
    "statement": "ALTER TABLE `flight-events` ADD event_time AS `$rowtime`;"
  }
mcp__confluent__create-flink-statement
  {
    "statementName": "gcc-watermark-modify",
    "catalogName":   "<environment-name>",
    "databaseName":  "<cluster-name>",
    "computePoolId": "<FLINK_COMPUTE_POOL_ID>",
    "statement": "ALTER TABLE `flight-events` MODIFY WATERMARK FOR event_time AS event_time - INTERVAL '2' SECOND;"
  }
```
Next Verify
```
Run "DESCRIBE `flight-events`;"
```

### Using Confluent Cloud UI

1. **Environment → Flink → Compute pools → gcc-pool → Open SQL workspace**
2. Paste and run `Step 1a` from `flink/01_add_watermarks.sql`
3. Open a **new** editor box (+), paste and run `Step 1b`

Verify with:
```sql
DESCRIBE `flight-events`;
```
You should see typed columns including `event_time` with a WATERMARK declaration.

---

## Step 3.2 — Create the Alerts Table

### Using Bob

```
Create the ops-alerts output table using flink/02_alerts_table.sql
```
```text
mcp__confluent__create-flink-statement
  {
    "statementName": "gcc-create-alerts-table",
    "catalogName":   "<environment-name>",
    "databaseName":  "<cluster-name>",
    "computePoolId": "<FLINK_COMPUTE_POOL_ID>",
    "statement": "<full contents of flink/02_alerts_table.sql>"
  }
```

### Using Confluent Cloud UI

Paste and run the full contents of `flink/02_alerts_table.sql` in a new SQL workspace box.

---

## Step 3.3 — Deploy the Anomaly Detection Job

> This is a **long-running streaming job**. Once started it shows **Running** status permanently — that is expected. Do NOT stop it unless you want anomaly detection to halt.

### Using Bob

```
Deploy the anomaly detection job from flink/03_anomaly_detection_ai.sql
as Flink statement named gate-change-anomaly-detection
```
```text
mcp__confluent__create-flink-statement
  {
    "statementName": "gate-change-anomaly-detection",
    "catalogName":   "<environment-name>",
    "databaseName":  "<cluster-name>",
    "computePoolId": "<FLINK_COMPUTE_POOL_ID>",
    "statement": "<full contents of flink/03_anomaly_detection_ai.sql>"
  }
```

Verify it is Running:
```
List my Flink statements and confirm gate-change-anomaly-detection is running
```
```text
mcp__confluent__list-flink-statements
```

### Using Confluent Cloud UI

Paste the full contents of `flink/03_anomaly_detection_ai.sql` into a new SQL workspace box and click **Run**.

---

## Step 3.4 — Wait for Warmup and Test

> Flink needs ~20 data windows (≈ **3 minutes**) before it starts scoring anomalies. No alerts will appear before that.

After 3 minutes, inject a test anomaly:

```bash
# From the gate-change-cascade/ directory with .venv active
python -m simulator.anomaly_injector AX303 schedule gate_wait --intensity 4.0
```

Or use the Streamlit dashboard sidebar: select flight AX303, metric `gate_wait`, intensity 4.0 → **Inject**.

Check for alerts with Bob:
```
Read the latest results from Flink statement gate-change-anomaly-detection
```
```text
mcp__confluent__read-flink-statement
  { "statementName": "gate-change-anomaly-detection", "timeoutInMilliseconds": 10000 }
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Schema not found` on ALTER TABLE | Simulator hasn't produced yet — wait 10s, retry |
| `Table already exists` on CREATE TABLE | `DROP TABLE IF EXISTS \`ops-alerts\`` then re-run |
| No anomalies after 5 min | Confirm job is Running; confirm anomaly_injector is active (`--list`) |
| `Authentication failed` on Flink | Use Global API key for `CONFLUENT_API_KEY`, not cluster-scoped |

---

**Next:** [05-wxa-agents.md](05-wxa-agents.md)
