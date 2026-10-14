"""investigator-api — gate-change-cascade edition.

Runs inside IBM Code Engine and exposes HTTPS endpoints the watsonx Orchestrate
agent tools and the Streamlit dashboard call at runtime.

No database dependency — all historical data is served by query_flight_history
(TableFlow/Iceberg via the ADK tool). This service only tails Kafka topics for
live telemetry and stores the cross-process agent activity log in memory.

Endpoints:
  GET  /healthz
  GET  /stream_window?entity_id=...&stream=schedule&metric=...&window_seconds=30
  GET  /recent_anomalies?entity_id=...&stream=schedule&metric=...&hours=24
  POST /agent_activity            body: arbitrary JSON
  GET  /agent_activity?limit=200
  DELETE /agent_activity
"""

from __future__ import annotations

import json
import os
import threading
import time
from collections import deque
from typing import Optional

from confluent_kafka import Consumer, KafkaError, TopicPartition
from fastapi import FastAPI, Query, Request

# ---------------------------------------------------------------------------
# Kafka config — reads KAFKA_API_KEY / KAFKA_API_SECRET (cluster-scoped)
# ---------------------------------------------------------------------------
KAFKA_CONFIG = {
    "bootstrap.servers":  os.getenv("CONFLUENT_BOOTSTRAP_SERVERS", ""),
    "security.protocol":  "SASL_SSL",
    "sasl.mechanisms":    "PLAIN",
    "sasl.username":      os.getenv("KAFKA_API_KEY", ""),
    "sasl.password":      os.getenv("KAFKA_API_SECRET", ""),
    "group.id":           f"gcc-investigator-{os.getpid()}",
    "auto.offset.reset":  "latest",
    "enable.auto.commit": False,
}

# Topic names — gate-change-cascade only has schedule telemetry and ops-alerts
FLIGHT_TOPIC  = "flight-events"
ALERTS_TOPIC  = "ops-alerts"

STREAM_TOPICS = {
    "schedule": FLIGHT_TOPIC,
}

# ---------------------------------------------------------------------------
# In-memory agent activity log
# Bounded deque so the container never OOMs.
# ---------------------------------------------------------------------------
_ACTIVITY_LOCK = threading.Lock()
_ACTIVITY_LOG: deque[dict] = deque(maxlen=2000)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="gate-change-cascade investigator-api", version="1.0")


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/healthz")
def healthz():
    bs = KAFKA_CONFIG.get("bootstrap.servers", "")
    return {"status": "ok", "kafka_configured": bool(bs)}


# ---------------------------------------------------------------------------
# Kafka helpers
# ---------------------------------------------------------------------------
def _kafka_cfg_from_request(request: Request) -> Optional[dict]:
    """Allow per-request credential override via request headers.
    Useful when the service is shared across multiple demo clusters."""
    bs = request.headers.get("x-confluent-bootstrap-servers", "")
    if not bs:
        return None
    return {
        **KAFKA_CONFIG,
        "bootstrap.servers": bs,
        "sasl.username": request.headers.get("x-kafka-api-key", ""),
        "sasl.password": request.headers.get("x-kafka-api-secret", ""),
    }


def _tail_topic(
    topic: str,
    lookback_seconds: int,
    max_messages: int = 5000,
    deadline_seconds: float = 5.0,
    kafka_cfg: Optional[dict] = None,
) -> list[dict]:
    """Return parsed JSON dicts from *topic* covering the last *lookback_seconds*.
    Returns an empty list if Kafka is not configured or no messages fall in the window."""
    cfg = {**(kafka_cfg or KAFKA_CONFIG), "group.id": f"gcc-api-tail-{os.getpid()}-{time.time_ns()}"}
    if not cfg.get("bootstrap.servers"):
        return []

    consumer = Consumer(cfg)
    try:
        cluster_md = consumer.list_topics(topic, timeout=5)
        if topic not in cluster_md.topics:
            return []
        partitions = list(cluster_md.topics[topic].partitions.keys())
        tps = [TopicPartition(topic, p) for p in partitions]
        cutoff_ms = int((time.time() - lookback_seconds) * 1000)
        offsets = consumer.offsets_for_times(
            [TopicPartition(topic, p, cutoff_ms) for p in partitions], timeout=5
        )
        assign = [
            TopicPartition(tp.topic, tp.partition, off.offset)
            for tp, off in zip(tps, offsets)
            if off.offset >= 0
        ]
        if not assign:
            return []
        consumer.assign(assign)

        out: list[dict] = []
        deadline = time.time() + deadline_seconds
        while time.time() < deadline and len(out) < max_messages:
            msg = consumer.poll(0.3)
            if msg is None:
                break
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    break
                continue
            try:
                raw = msg.value()
                if raw and raw[:1] == b"\x00":
                    raw = raw[5:]  # strip Schema Registry magic prefix
                out.append(json.loads(raw.decode("utf-8")))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
        return out
    finally:
        consumer.close()


# ---------------------------------------------------------------------------
# /stream_window
# Returns a per-metric summary of the last N seconds of schedule telemetry
# for one aircraft (entity_id). Optionally filtered by metric name.
# ---------------------------------------------------------------------------
@app.get("/stream_window")
def stream_window(
    request: Request,
    entity_id: str,
    stream: Optional[str] = "schedule",
    metric: Optional[str] = None,
    window_seconds: int = 30,
):
    if window_seconds <= 0 or window_seconds > 3600:
        return {"status": "error", "error": "window_seconds must be 1..3600"}

    if stream and stream not in STREAM_TOPICS:
        return {"status": "error", "error": f"unknown stream {stream!r}. Use: schedule"}

    kafka_cfg = _kafka_cfg_from_request(request)
    topic = STREAM_TOPICS.get(stream or "schedule", FLIGHT_TOPIC)
    rows = _tail_topic(topic, window_seconds, kafka_cfg=kafka_cfg)

    # Filter to this aircraft
    filtered = [
        r for r in rows
        if r.get("aircraft_id") == entity_id or r.get("entity_id") == entity_id
    ]
    if metric:
        filtered = [r for r in filtered if r.get("metric") == metric]

    if not filtered:
        return {
            "status":         "ok",
            "entity_id":      entity_id,
            "stream":         stream,
            "metric":         metric,
            "window_seconds": window_seconds,
            "count":          0,
        }

    # Group by metric → summary
    by_metric: dict[str, list] = {}
    for r in filtered:
        by_metric.setdefault(r.get("metric", "unknown"), []).append(r)

    summaries: dict[str, dict] = {}
    for m_name, records in by_metric.items():
        values = [v["value"] for v in records if isinstance(v.get("value"), (int, float))]
        if not values:
            continue
        summaries[m_name] = {
            "count":      len(values),
            "min":        round(min(values), 4),
            "max":        round(max(values), 4),
            "avg":        round(sum(values) / len(values), 4),
            "unit":       records[-1].get("unit"),
            "last_value": records[-1].get("value"),
            "last_ts":    records[-1].get("timestamp"),
        }

    return {
        "status":         "ok",
        "entity_id":      entity_id,
        "stream":         stream,
        "metric":         metric,
        "window_seconds": window_seconds,
        "count":          len(filtered),
        "summaries":      {"schedule": summaries},
    }


# ---------------------------------------------------------------------------
# /recent_anomalies
# Tails ops-alerts for the last N hours, filtered by entity/metric.
# ---------------------------------------------------------------------------
@app.get("/recent_anomalies")
def recent_anomalies(
    request: Request,
    entity_id: Optional[str] = None,
    stream: Optional[str] = None,
    metric: Optional[str] = None,
    hours: int = 24,
):
    if hours <= 0 or hours > 168:
        return {"status": "error", "error": "hours must be between 1 and 168"}

    kafka_cfg = _kafka_cfg_from_request(request)
    raw_rows = _tail_topic(
        ALERTS_TOPIC,
        hours * 3600,
        max_messages=1000,
        deadline_seconds=8.0,
        kafka_cfg=kafka_cfg,
    )

    def _ts(r: dict) -> str:
        return r.get("detected_at") or r.get("event_time") or r.get("timestamp") or ""

    filtered: list[dict] = []
    for r in raw_rows:
        if entity_id and r.get("entity_id") != entity_id:
            continue
        if stream and r.get("stream") != stream:
            continue
        if metric and r.get("metric") != metric:
            continue
        if r.get("is_anomaly") is False:
            continue
        filtered.append(r)

    filtered.sort(key=_ts, reverse=True)
    out = [
        {
            "ts":            _ts(r) or None,
            "entity_id":     r.get("entity_id"),
            "stream":        r.get("stream"),
            "metric":        r.get("metric"),
            "value":         r.get("value"),
            "unit":          r.get("unit"),
            "anomaly_score": r.get("anomaly_score"),
            "hub":           r.get("hub"),
        }
        for r in filtered
    ]
    return {
        "status":    "ok",
        "entity_id": entity_id,
        "stream":    stream,
        "metric":    metric,
        "hours":     hours,
        "row_count": len(out),
        "anomalies": out,
    }


# ---------------------------------------------------------------------------
# Agent activity log — in-memory, shared between alert_consumer and dashboard
# ---------------------------------------------------------------------------
@app.post("/agent_activity")
async def append_agent_activity(request: Request):
    entry = await request.json()
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    entry.setdefault("ts", ts)
    with _ACTIVITY_LOCK:
        _ACTIVITY_LOG.append({"payload": entry})
    return {"status": "ok", "ts": ts}


@app.get("/agent_activity")
def list_agent_activity(limit: int = Query(200, ge=1, le=2000)):
    with _ACTIVITY_LOCK:
        items = list(_ACTIVITY_LOG)
    items.reverse()   # newest first
    items = items[:limit]
    return {"status": "ok", "items": items, "count": len(items)}


@app.delete("/agent_activity")
def clear_agent_activity():
    with _ACTIVITY_LOCK:
        deleted = len(_ACTIVITY_LOG)
        _ACTIVITY_LOG.clear()
    return {"status": "ok", "deleted": deleted}
