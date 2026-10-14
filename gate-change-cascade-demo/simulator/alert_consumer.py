"""Alert consumer — reads ops-alerts from Kafka, dispatches to the
watsonx Orchestrate Supervisor Agent, and POSTs activity records to the
investigator-api (or a local log for dry runs).
"""

import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

from confluent_kafka import Consumer, KafkaError
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the gate-change-cascade root (two levels up: simulator/ -> root)
_ENV = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(_ENV)

KAFKA_CONFIG = {
    "bootstrap.servers": os.getenv("CONFLUENT_BOOTSTRAP_SERVERS", ""),
    "security.protocol": "SASL_SSL",
    "sasl.mechanisms":   "PLAIN",
    "sasl.username":     os.getenv("KAFKA_API_KEY", ""),
    "sasl.password":     os.getenv("KAFKA_API_SECRET", ""),
    "group.id":          "gcc-alert-consumer",
    "auto.offset.reset": "latest",
    # keepalive / session tuning for high-latency connections
    "socket.keepalive.enable":      True,
    "session.timeout.ms":           60000,
    "heartbeat.interval.ms":        10000,
    "max.poll.interval.ms":         600000,
    "reconnect.backoff.ms":         1000,
    "reconnect.backoff.max.ms":     10000,
}

OPS_ALERTS_TOPIC     = "ops-alerts"
IAM_TOKEN_URL        = "https://iam.cloud.ibm.com/identity/token"
ACTIVITY_LOG         = os.getenv("AGENT_ACTIVITY_LOG", "/tmp/gcc_agent_activity.log")
INVESTIGATOR_API_URL = os.getenv("INVESTIGATOR_API_URL", "").rstrip("/")

_token_lock    = threading.Lock()
_token_cache   = {"token": None, "expires_at": 0.0}
_inflight: set[str] = set()
_inflight_lock = threading.Lock()


def _get_bearer_token() -> str:
    with _token_lock:
        now = time.time()
        if _token_cache["token"] and _token_cache["expires_at"] - 60 > now:
            return _token_cache["token"]
        data = urllib.parse.urlencode({
            "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
            "apikey":     os.getenv("WO_API_KEY", "").strip(),
        }).encode()
        req = urllib.request.Request(
            IAM_TOKEN_URL, data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode())
        _token_cache["token"] = body["access_token"]
        _token_cache["expires_at"] = now + body.get("expires_in", 3600)
        return _token_cache["token"]


def _append_activity(entry: dict) -> None:
    entry["ts"] = datetime.now().isoformat(timespec="seconds")

    if INVESTIGATOR_API_URL:
        try:
            payload = json.dumps(entry).encode()
            req = urllib.request.Request(
                f"{INVESTIGATOR_API_URL}/agent_activity",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=15)
            return
        except Exception as post_exc:
            print(f"[alert_consumer] activity POST failed: {post_exc}")
            # fall through to local log

    try:
        with open(ACTIVITY_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:
        pass


def _invoke_agent_worker(alert: dict, alert_key: str) -> None:
    # Route all alerts to the supervisor agent
    agent_id    = os.getenv("WO_SUPERVISOR_AGENT_ID", "").strip()
    wo_instance = os.getenv("WO_INSTANCE", "").rstrip("/")
    wo_api_key  = os.getenv("WO_API_KEY", "").strip()

    if not (agent_id and wo_instance and wo_api_key):
        print("[alert_consumer] WO_SUPERVISOR_AGENT_ID / WO_INSTANCE / WO_API_KEY not set — skipping dispatch")
        with _inflight_lock:
            _inflight.discard(alert_key)
        return

    try:
        token = _get_bearer_token()
        url   = f"{wo_instance}/v1/orchestrate/{agent_id}/chat/completions"
        payload = json.dumps({
            "messages":    [{"role": "user", "content": json.dumps(alert)}],
            "stream":      False,
            "temperature": 0.2,
            "max_tokens":  2000,
        }).encode()
        req = urllib.request.Request(
            url, data=payload,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode())
        choices = body.get("choices") or []
        content = ((choices[0].get("message") or {}).get("content") or "") if choices else ""
        _append_activity({
            "type":       "response",
            "entity_id":  alert.get("entity_id"),
            "stream":     alert.get("stream"),
            "metric":     alert.get("metric"),
            "text":       content or json.dumps(body)[:2000],
        })
    except urllib.error.HTTPError as exc:
        _append_activity({
            "type":      "response",
            "entity_id": alert.get("entity_id"),
            "text":      f"ERROR HTTP {exc.code}: {exc.read().decode(errors='replace')[:500]}",
        })
    except Exception as exc:
        _append_activity({
            "type":      "response",
            "entity_id": alert.get("entity_id"),
            "text":      f"ERROR: {exc}",
        })
    finally:
        with _inflight_lock:
            _inflight.discard(alert_key)


def dispatch_alert(alert: dict) -> None:
    key = f"{alert.get('entity_id')}:{alert.get('stream')}:{alert.get('metric')}:{alert.get('timestamp', '')}"
    with _inflight_lock:
        if key in _inflight:
            return
        _inflight.add(key)
    _append_activity({"type": "alert", "alert": alert})
    threading.Thread(target=_invoke_agent_worker, args=(alert, key), daemon=True).start()


def run():
    consumer = Consumer(KAFKA_CONFIG)
    consumer.subscribe([OPS_ALERTS_TOPIC])
    print(f"GCC alert consumer listening on {OPS_ALERTS_TOPIC} ...")

    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() != KafkaError._PARTITION_EOF:
                    print(f"Kafka error: {msg.error()}")
                continue
            try:
                raw = msg.value()
                if raw[:1] == b"\x00":
                    raw = raw[5:]
                alert = json.loads(raw.decode("utf-8"))
                dispatch_alert(alert)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                print(f"Decode error: {exc}")
    except KeyboardInterrupt:
        pass
    finally:
        consumer.close()


if __name__ == "__main__":
    run()
