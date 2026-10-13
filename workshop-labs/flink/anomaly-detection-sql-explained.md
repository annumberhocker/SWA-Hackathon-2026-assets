# Understanding the Flink Anomaly Detection SQL

This document explains the architecture and logic of [`workshop-labs/flink/anomaly_detection_materialized.sql`](anomaly_detection_materialized.sql).

## Overview

A single `CREATE OR ALTER MATERIALIZED TABLE` statement performs three operations in one shot:

1. **Creates (or evolves) the `ops-alerts` table** — defines all columns, sets the `WATERMARK`, and binds to the `ops-alerts` Kafka topic without requiring manual topic creation or a separate DDL step.
2. **Runs the streaming query continuously** — reads from `flight-events`, applies a 2-second tumbling window per aircraft + metric, calls Confluent's `AI_DETECT_ANOMALIES` function, and writes only confirmed anomalies to `ops-alerts`.
3. **Executes background refresh continuously** — The DDL (Data Definition Language — SQL commands used to define database and table structures) statement itself shows `COMPLETED` once registered, while the managed background refresh job runs continuously in the background. `START_MODE = RESUME_OR_FROM_BEGINNING` means Flink resumes from where it left off if the table is restarted.

---

## Query Architecture

The query is structured using two CTEs (Common Table Expressions — temporary named result sets defined with `WITH ... AS` blocks):

### 1. `windowed_schedule` (Window Aggregation)
Groups raw telemetry events into 2-second tumbling windows:
```sql
TUMBLE(TABLE `SWA-Hackathon`.`cluster-gcc`.`flight-events`, DESCRIPTOR(event_time), INTERVAL '2' SECONDS)
```
and averages each metric (`AVG(value) AS avg_value`). This smooths short-term fluctuations and reduces noise before anomaly scoring.

### 2. `anomaly_results` (AI Anomaly Detection)
Calls `AI_DETECT_ANOMALIES` as an analytic function over an unbounded window partitioned by `(entity_id, stream, metric)` ordered by `window_time`:
```sql
AI_DETECT_ANOMALIES(
    avg_value,
    window_time,
    JSON_OBJECT(
        'minContextSize' VALUE 5,
        'maxContextSize' VALUE 512,
        'confidencePercentage' VALUE 99.0
    )
) OVER (
    PARTITION BY entity_id, `stream`, metric
    ORDER BY window_time
)
```
This gives the machine learning model full historical context per aircraft-metric pair to establish an adaptive baseline.

### 3. Final Filtering & Projection
The outer `SELECT` filters results to only high-confidence anomalies:
```sql
WHERE is_anomaly = TRUE AND anomaly_score > 0.95
```
Only confirmed anomalies are written to the `ops-alerts` Kafka topic.

---

## Key Tuning Parameters

| Parameter | Value | Purpose |
|---|---|---|
| `minContextSize` | `5` | Requires 5 completed 2-second windows (~10 seconds) of baseline history before scoring begins. During this warmup period, no alerts are produced. |
| `maxContextSize` | `512` | Maximum history window maintained in state per entity-metric pair. |
| `confidencePercentage` | `99.0` | Confidence threshold required before flagging an event as an anomaly. |
| `anomaly_score > 0.95` | `0.95` | Additional threshold on normalized deviation to eliminate low-severity noise. |
| `START_MODE` | `RESUME_OR_FROM_BEGINNING` | Resumes from where it left off if restarted, or from the beginning if newly created. |
