-- 02_alerts_table.sql
-- ============================================================================
-- Creates the ops-alerts topic/table that Flink will write anomaly events into.
-- Run this BEFORE running 03_anomaly_detection_ai.sql.
-- ============================================================================

-- ⚠️  IMPORTANT — DO NOT use DISTRIBUTED INTO when the ops-alerts Kafka topic
--    already exists (created via MCP or the Confluent UI).
--    Using DISTRIBUTED INTO on a pre-existing topic causes a schema conflict
--    because Flink auto-infers a raw `key: BYTES` column that breaks the INSERT.
--    Use WITH ('kafka.cleanup-policy'='delete') instead — Flink will bind to
--    the existing topic without re-partitioning it.
--
--    If you need to recreate from scratch:
--      1. DROP TABLE `ops-alerts`;
--      2. Delete the ops-alerts topic in Confluent Cloud.
--      3. Re-run this statement.

CREATE TABLE IF NOT EXISTS `ops-alerts` (
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
);

