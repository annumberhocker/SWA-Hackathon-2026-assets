-- add_watermarks.sql
-- ============================================================================
-- Adds an event-time column and watermark to the flight-events Flink table.
--
-- IMPORTANT — RUN EACH STATEMENT SEPARATELY
-- Confluent Cloud Flink only accepts ONE statement per Run click.
--
-- ⚠️  PREREQUISITE — DO THIS BEFORE RUNNING ANY STATEMENT BELOW:
--
--   1. Start the flight_producer.py simulator and confirm it is producing.
--   2. In the Confluent UI go to:
--          Topics → flight-events → Messages
--      and confirm rows are arriving.
--   3. In the Flink SQL workspace run the verification query below and confirm
--      you see typed columns (flight_number STRING, aircraft_id STRING, etc.)
--      rather than just key / value as BYTES:
--
--        DESCRIBE `flight-events`;
--
--   If you only see BYTES columns, the simulator has not published a schema
--   yet.  Wait 10 seconds and re-check before proceeding.
--
-- ============================================================================

-- ─────────────────────────────────────────────────────────────────────────────
-- Step 1 — Add the event_time computed column.
-- Run this statement ALONE and wait for status COMPLETED before Step 2.
-- If the column already exists (from a previous run) this statement will FAIL;
-- that is expected and safe — proceed directly to Step 2.
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE `flight-events`
    ADD event_time AS `$rowtime`;


-- ─────────────────────────────────────────────────────────────────────────────
-- Step 2 — Attach the watermark strategy.
-- Run this statement ALONE after Step 1 completes (or after skipping Step 1).
-- The 2-second lag tolerates minor out-of-order delivery from the producer.
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE `flight-events`
    MODIFY WATERMARK FOR event_time AS event_time - INTERVAL '2' SECOND;
