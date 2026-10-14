-- 01_add_watermarks.sql
-- ============================================================================
-- IMPORTANT — RUN EACH STATEMENT SEPARATELY
-- ============================================================================
-- Confluent Cloud Flink only accepts ONE statement per Run click.
-- Run order: 01 (this file) → 02 → 03
--
-- ⚠️  PREREQUISITE — DO THIS BEFORE RUNNING ANY STATEMENT BELOW:
--
--   1. Start the simulator and confirm it is producing messages.
--   2. In the Confluent UI go to Topics → flight-events → Messages
--      and confirm rows are arriving.
--   3. Run this verification query and confirm you see typed columns
--      (flight_number STRING, aircraft_id STRING, etc.) — NOT just key/val BYTES:
--
--        DESCRIBE `flight-events`;
--
--   If you see only BYTES, the simulator has not published yet.
--   Wait 10 seconds and re-check before proceeding.
--
-- ============================================================================

-- ─────────────────────────────────────────────────────────────────────────────
-- Step 1a — Run this statement ALONE first. Wait for COMPLETED before Step 1b.
-- If event_time already exists (from a previous run) this will FAIL — that is
-- expected and safe. Proceed directly to Step 1b.
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE `flight-events`
    ADD event_time AS `$rowtime`;


-- ─────────────────────────────────────────────────────────────────────────────
-- Step 1b — Run this statement ALONE after Step 1a completes (or if 1a was
-- skipped because event_time already existed).
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE `flight-events`
    MODIFY WATERMARK FOR event_time AS event_time - INTERVAL '2' SECOND;
