- anomaly_detection_materialized.sql
-- ============================================================================
-- Single CREATE OR ALTER MATERIALIZED TABLE that replaces BOTH:
--   alerts_table.sql       (CREATE TABLE `ops-alerts`)
--   anomaly_detection.sql  (INSERT INTO `ops-alerts` ...)
--
-- The materialized table owns both the `ops-alerts` table definition and the
-- continuous anomaly-detection query. Paste the whole file and click Run.
-- Status goes to Running and stays there. DO NOT stop it manually.
-- ============================================================================
-- Architecture:
--   windowed_schedule   10s TUMBLE window avg of flight-events metrics
--   anomaly_results     AI_DETECT_ANOMALIES per (entity_id, metric)
--   final SELECT        score=[0,1], filter is_anomaly=TRUE AND score > 0.95
--
-- minContextSize=20 → minimum data points before detection begins (~3.5 min warmup at 10s windows).
-- Raise the 0.95 threshold to reduce false-positive alert volume.
--
-- Re-running this statement evolves the table in place (same `ops-alerts`
-- topic). Each evolution discards window/anomaly state, so detection re-warms.
--
-- ⚠️  If `ops-alerts` already exists as a regular table (from alerts_table.sql),
--    this statement adopts it as a materialized table. STOP the old
--    INSERT INTO `ops-alerts` statement first to avoid duplicate alerts.
--    The column list below matches the existing table so the Schema Registry
--    schema stays compatible. Do NOT add DISTRIBUTED INTO for an existing topic.
-- ============================================================================

CREATE OR ALTER MATERIALIZED TABLE `IBM-Hackathon-demo-test`.`REPLACE_WITH_YOUR_CLUSTER`.`ops-alerts` (
    entity_id       STRING,
    `stream`        STRING,
    metric          STRING,
    `value`         DOUBLE,
    unit            STRING,
    anomaly_score   DOUBLE,
    is_anomaly      BOOLEAN,
    hub             STRING,
    detected_at     TIMESTAMP(3),
    event_time      TIMESTAMP(3),
    WATERMARK FOR event_time AS event_time - INTERVAL '2' SECOND
)
WITH (
    'kafka.cleanup-policy' = 'delete'
)
START_MODE = RESUME_OR_FROM_BEGINNING
AS
WITH windowed_schedule AS (
    SELECT
        aircraft_id        AS entity_id,
        'schedule'         AS `stream`,
        metric,
        unit,
        hub,
        window_time,
        AVG(`value`)       AS avg_value
    FROM TABLE(
        TUMBLE(TABLE `IBM-Hackathon-demo-test`.`cluster-gcc`.`flight-events`, DESCRIPTOR(event_time), INTERVAL '10' SECONDS)
    )
    GROUP BY aircraft_id, metric, unit, hub, window_start, window_end, window_time
),

anomaly_results AS (
    SELECT
        entity_id,
        `stream`,
        metric,
        avg_value,
        unit,
        hub,
        window_time,
        AI_DETECT_ANOMALIES(
            avg_value,
            window_time,
            JSON_OBJECT(
                'minContextSize' VALUE 20,
                'maxContextSize' VALUE 512,
                'confidencePercentage' VALUE 99.0
            )
        ) OVER (
            PARTITION BY entity_id, `stream`, metric
            ORDER BY window_time
            RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS anomaly
    FROM windowed_schedule
)

SELECT
    entity_id,
    `stream`,
    metric,
    avg_value       AS `value`,
    unit,
    LEAST(1.0, ABS(avg_value - anomaly.forecast_value) /
         NULLIF(anomaly.upper_bound - anomaly.lower_bound, 0)) AS anomaly_score,
    anomaly.is_anomaly  AS is_anomaly,
    hub,
    CAST(CURRENT_TIMESTAMP AS TIMESTAMP(3)) AS detected_at,
    window_time         AS event_time
FROM anomaly_results
WHERE anomaly.is_anomaly = TRUE
  AND ABS(avg_value - anomaly.forecast_value)
        / NULLIF(anomaly.upper_bound - anomaly.lower_bound, 0) > 0.95;
