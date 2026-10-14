"""Gate Change Cascade — Streamlit Dashboard (IBM Carbon style).

Displays the real-time flight-events stream and anomaly alerts.
Agent Activity panel shows watsonx Orchestrate supervisor agent responses.
"""

import html
import json
import os
import re
import sys
import time
import uuid
import threading
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime

import pandas as pd
import streamlit as st
from confluent_kafka import Consumer, KafkaError
from dotenv import load_dotenv

# ── Env ────────────────────────────────────────────────────────────────────────
ENV_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(ENV_FILE)

st.set_page_config(
    page_title="Gate Change Cascade",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── IBM Carbon design tokens ──────────────────────────────────────────────────
CSS = """
<style>
:root {
  --cds-background: #ffffff;
  --cds-layer-01: #f4f4f4;
  --cds-border-subtle: #e0e0e0;
  --cds-text-primary: #161616;
  --cds-text-secondary: #525252;
  --cds-interactive: #0f62fe;
  --cds-support-error: #da1e28;
  --cds-support-warning: #f1c21b;
  --cds-support-success: #24a148;
}
.cds-masthead {
  background: #161616; color: #ffffff;
  padding: 10px 16px; border-radius: 4px;
  display: flex; align-items: center; gap: 16px; margin-bottom: 4px;
}
.cds-wordmark { font-size: 18px; font-weight: 600; letter-spacing: .5px; }
.cds-status-pill {
  margin-left: auto; font-size: 11px; padding: 2px 8px;
  background: #24a148; border-radius: 8px; color: #fff;
}
.cds-caption { font-size: 12px; color: var(--cds-text-secondary); margin-bottom: 12px; }
.cds-card {
  background: var(--cds-layer-01); border: 1px solid var(--cds-border-subtle);
  border-radius: 4px; padding: 10px 12px; margin-bottom: 8px;
}
.cds-flight-status { border-radius: 4px; padding: 8px 10px; margin-bottom: 6px; }
.cds-flight-status.ok   { background: #defbe6; border-left: 3px solid #24a148; }
.cds-flight-status.warn { background: #fdf6dd; border-left: 3px solid #f1c21b; }
.cds-flight-status.alert{ background: #fff1f1; border-left: 3px solid #da1e28; }
.cds-flight-header { display: flex; align-items: center; gap: 8px; margin-bottom: 2px; }
.cds-flight-ref  { font-size: 13px; font-weight: 600; }
.cds-status-chip {
  font-size: 10px; padding: 1px 6px; border-radius: 3px; font-weight: 700;
}
.cds-status-chip.ok   { background: #24a148; color: #fff; }
.cds-status-chip.warn { background: #f1c21b; color: #161616; }
.cds-status-chip.alert{ background: #da1e28; color: #fff; }
.cds-flight-values { font-size: 11px; color: var(--cds-text-secondary); }
.cds-log { font-family: monospace; font-size: 11px; padding: 2px 4px; border-radius: 2px; }
.cds-log-alert  { background: #fff1f1; color: #da1e28; }
.cds-log-detail { background: #f4f4f4; color: #161616; }
.cds-log-separator { border-top: 1px solid var(--cds-border-subtle); margin: 4px 0; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
KAFKA_CONFIG = {
    "bootstrap.servers": os.getenv("CONFLUENT_BOOTSTRAP_SERVERS", ""),
    "security.protocol": "SASL_SSL",
    "sasl.mechanisms":   "PLAIN",
    "sasl.username":     os.getenv("KAFKA_API_KEY", ""),
    "sasl.password":     os.getenv("KAFKA_API_SECRET", ""),
    "group.id":          f"gcc-dash-{uuid.uuid4().hex[:8]}",
    "auto.offset.reset": "latest",
    "max.poll.interval.ms":         600000,
    # keepalive / session tuning for high-latency connections
    "socket.keepalive.enable":      True,
    "session.timeout.ms":           60000,
    "heartbeat.interval.ms":        10000,
    "reconnect.backoff.ms":         1000,
    "reconnect.backoff.max.ms":     10000,
}

FLIGHT_EVENTS_TOPIC = "flight-events"
OPS_ALERTS_TOPIC    = "ops-alerts"
ALL_TOPICS          = [FLIGHT_EVENTS_TOPIC, OPS_ALERTS_TOPIC]

AIRCRAFT = ["N101AX", "N202AX", "N303AX", "N404AX"]
FLIGHTS  = {"N101AX": "AX101", "N202AX": "AX202", "N303AX": "AX303", "N404AX": "AX404"}

SCHEDULE_METRICS = ["departure_delay", "gate_wait", "turnaround_time"]
SCHEDULE_UNITS   = {
    "departure_delay": "min",
    "gate_wait":       "min",
    "turnaround_time": "min",
}

DATA_VIZ_COLORS = ["#0f62fe", "#6929c4", "#009d9a", "#9f1853"]
AIRCRAFT_COLORS = dict(zip(AIRCRAFT, DATA_VIZ_COLORS))

ACTIVITY_LOG          = os.getenv("AGENT_ACTIVITY_LOG", "/tmp/gcc_agent_activity.log")
ANOMALY_FILE          = "/tmp/gcc_anomaly.json"
INVESTIGATOR_API_URL  = os.getenv("INVESTIGATOR_API_URL", "").rstrip("/")
SIMULATOR_CONTROL_URL = os.getenv("SIMULATOR_CONTROL_URL", "").rstrip("/")
MAX_POINTS            = 60

WO_INSTANCE          = os.getenv("WO_INSTANCE", "").rstrip("/")
WO_API_KEY           = os.getenv("WO_API_KEY", "").strip()
WO_SUPERVISOR_AGENT_ID = os.getenv("WO_SUPERVISOR_AGENT_ID", "").strip()

# ── IAM token cache ───────────────────────────────────────────────────────────
IAM_TOKEN_URL   = "https://iam.cloud.ibm.com/identity/token"
_token_lock     = threading.Lock()
_token_cache    = {"token": None, "expires_at": 0.0}
_triage_inflight: set[str] = set()
_triage_lock    = threading.Lock()


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
            payload = json.dumps({"payload": entry}).encode()
            req = urllib.request.Request(
                f"{INVESTIGATOR_API_URL}/agent_activity",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=5)
            return
        except Exception:
            pass
    try:
        with open(ACTIVITY_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:
        pass


def _triage_worker(alert: dict, alert_key: str, agent_id: str) -> None:
    try:
        token = _get_bearer_token()
        url   = f"{WO_INSTANCE}/v1/orchestrate/{agent_id}/chat/completions"
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
        with urllib.request.urlopen(req, timeout=180) as resp:
            body = json.loads(resp.read().decode())
        choices = body.get("choices") or []
        content = ((choices[0].get("message") or {}).get("content") or "") if choices else ""
        _append_activity({
            "type":      "response",
            "entity_id": alert.get("entity_id"),
            "text":      content or json.dumps(body)[:2000],
        })
    except Exception as exc:
        _append_activity({
            "type":      "response",
            "entity_id": alert.get("entity_id"),
            "text":      f"ERROR: {exc}",
        })
    finally:
        with _triage_lock:
            _triage_inflight.discard(alert_key)


def dispatch_triage(alert: dict) -> None:
    agent_id = (
        st.session_state.get("supervisor_agent_id_input", "").strip()
        or WO_SUPERVISOR_AGENT_ID
    )
    if not (agent_id and WO_INSTANCE and WO_API_KEY):
        return
    key = f"{alert.get('entity_id')}:{alert.get('stream')}:{alert.get('metric')}:{alert.get('timestamp', '')}"
    with _triage_lock:
        if key in _triage_inflight:
            return
        _triage_inflight.add(key)
    _append_activity({"type": "alert", "alert": alert})
    threading.Thread(target=_triage_worker, args=(alert, key, agent_id), daemon=True).start()


# ── Anomaly injection helpers ─────────────────────────────────────────────────
def load_anomaly_targets() -> list[dict]:
    if not os.path.exists(ANOMALY_FILE):
        return []
    try:
        with open(ANOMALY_FILE, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(data, list):
        return [t for t in data if isinstance(t, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def _write_targets(targets: list[dict]) -> None:
    if not targets:
        try:
            os.remove(ANOMALY_FILE)
        except FileNotFoundError:
            pass
        return
    with open(ANOMALY_FILE, "w") as f:
        json.dump(targets, f)


def inject_anomaly(
    entity_id: str,
    stream: str,
    metric: str,
    intensity: float = 3.0,
    details: dict | None = None,
) -> None:
    targets = [
        t for t in load_anomaly_targets()
        if not (t.get("entity_id") == entity_id
                and t.get("stream") == stream
                and t.get("metric") == metric)
    ]
    entry = {
        "entity_id":  entity_id,
        "stream":     stream,
        "metric":     metric,
        "start_time": time.time(),
        "intensity":  intensity,
    }
    if details:
        entry["details"] = details
    targets.append(entry)
    _write_targets(targets)


def clear_all_anomalies() -> None:
    _write_targets([])


# ── Simulator control ─────────────────────────────────────────────────────────
def _post_simulator_action(action: str) -> bool:
    if not SIMULATOR_CONTROL_URL:
        return False
    try:
        req = urllib.request.Request(
            f"{SIMULATOR_CONTROL_URL}/control",
            data=json.dumps({"action": action}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=4) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


# ── Session state ─────────────────────────────────────────────────────────────
def _reset_state(clear_tmp: bool = True) -> None:
    for key in list(st.session_state.keys()):
        st.session_state.pop(key, None)
    st.session_state.schedule_data  = defaultdict(lambda: defaultdict(list))
    st.session_state.alerts         = []
    st.session_state.readings_count = 0
    st.session_state.anomaly_count  = 0
    st.session_state.stream_stopped = True
    if clear_tmp:
        for path in (ANOMALY_FILE, ACTIVITY_LOG):
            try:
                os.remove(path)
            except FileNotFoundError:
                pass
    if INVESTIGATOR_API_URL:
        try:
            req = urllib.request.Request(
                f"{INVESTIGATOR_API_URL}/agent_activity", method="DELETE"
            )
            with urllib.request.urlopen(req, timeout=5):
                pass
        except Exception:
            pass


if os.getenv("RESET", "").lower() in ("1", "true", "yes", "on"):
    if "_reset_applied" not in st.session_state:
        _reset_state(clear_tmp=True)
        st.session_state._reset_applied = True

for _k, _v in {
    "schedule_data":  defaultdict(lambda: defaultdict(list)),
    "alerts":         [],
    "readings_count": 0,
    "anomaly_count":  0,
    "stream_stopped": True,
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ── Kafka consumer ─────────────────────────────────────────────────────────────
@st.cache_resource
def get_consumer():
    c = Consumer(KAFKA_CONFIG)
    c.subscribe(ALL_TOPICS)
    return c


def poll_messages(max_messages: int = 50):
    if st.session_state.get("stream_stopped"):
        return []
    consumer = get_consumer()
    out = []
    for _ in range(max_messages):
        msg = consumer.poll(timeout=0.02)
        if msg is None:
            break
        if msg.error():
            if msg.error().code() not in (KafkaError._PARTITION_EOF,
                                           KafkaError.UNKNOWN_TOPIC_OR_PART):
                st.error(f"Kafka error: {msg.error()}")
            continue
        try:
            raw = msg.value()
            if raw[:1] == b"\x00":
                raw = raw[5:]
            value = json.loads(raw.decode("utf-8"))
            value["_topic"] = msg.topic()
            out.append(value)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
    return out


# ── Activity log ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=1)
def read_activity_log(limit: int = 40) -> list[dict]:
    if INVESTIGATOR_API_URL:
        try:
            url = f"{INVESTIGATOR_API_URL}/agent_activity?limit={int(limit)}"
            with urllib.request.urlopen(url, timeout=1.5) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            items = body.get("items") or []
            return [it.get("payload") or {} for it in reversed(items)]
        except Exception:
            pass
    if not os.path.exists(ACTIVITY_LOG):
        return []
    try:
        with open(ACTIVITY_LOG, "r") as f:
            lines = f.readlines()[-limit:]
    except OSError:
        return []
    out = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


# ── Chart helpers ─────────────────────────────────────────────────────────────
def _build_chart_data(metric: str) -> "pd.DataFrame | None":
    frames = {}
    for ac in AIRCRAFT:
        readings = st.session_state.schedule_data.get(ac, {}).get(metric, [])
        if readings:
            df = pd.DataFrame(readings[-MAX_POINTS:])
            df["time"] = pd.to_datetime(df["time"])
            df = df.set_index("time")
            df = df[~df.index.duplicated(keep="last")]
            frames[ac] = df["value"]
    if not frames:
        return None
    combined = pd.DataFrame(frames).sort_index()
    return combined.ffill().bfill()


def _render_schedule_charts():
    st.markdown("<h5>✈️ Flight Schedule Metrics</h5>", unsafe_allow_html=True)
    for metric in SCHEDULE_METRICS:
        chart_data = _build_chart_data(metric)
        if chart_data is None or chart_data.empty:
            continue
        unit = SCHEDULE_UNITS.get(metric, "")
        st.markdown(
            f"<span class='cds-caption'>{metric.replace('_', ' ').title()} ({unit})</span>",
            unsafe_allow_html=True,
        )
        colors = [AIRCRAFT_COLORS[ac] for ac in chart_data.columns if ac in AIRCRAFT_COLORS]
        st.line_chart(chart_data, color=colors, height=150)


# ── Flight status cards ───────────────────────────────────────────────────────
def _render_flight_cards():
    alert_entities = {
        a.get("alert", {}).get("entity_id")
        for a in st.session_state.alerts
    }
    for ac in AIRCRAFT:
        flight_num = FLIGHTS.get(ac, ac)
        latest: dict[str, float] = {}
        for metric in SCHEDULE_METRICS:
            readings = st.session_state.schedule_data.get(ac, {}).get(metric, [])
            if readings:
                latest[metric] = readings[-1]["value"]

        delay = latest.get("departure_delay", 0.0)
        if flight_num in alert_entities or delay > 15:
            cls = "alert"
            chip_cls = "alert"
            status = "DELAYED"
        elif delay > 8:
            cls = "warn"
            chip_cls = "warn"
            status = "WATCH"
        else:
            cls = "ok"
            chip_cls = "ok"
            status = "ON TIME"

        vals_str = " | ".join(
            f"{m.replace('_', ' ')}: {v:.1f}"
            for m, v in latest.items()
        ) if latest else "No data yet"

        st.markdown(
            f"""<div class='cds-flight-status {cls}'>
              <div class='cds-flight-header'>
                <span class='cds-flight-ref'>{flight_num} ({ac})</span>
                <span class='cds-status-chip {chip_cls}'>{status}</span>
              </div>
              <div class='cds-flight-values'>{html.escape(vals_str)}</div>
            </div>""",
            unsafe_allow_html=True,
        )


# ── Activity panel ────────────────────────────────────────────────────────────
def _render_activity_panel():
    st.markdown("<h5>🤖 Agent Activity</h5>", unsafe_allow_html=True)
    entries = read_activity_log(limit=30)
    if not entries:
        st.markdown(
            "<p class='cds-caption'>No agent activity yet. "
            "Inject an anomaly to see the Supervisor Agent triage it.</p>",
            unsafe_allow_html=True,
        )
        return

    for entry in reversed(entries):
        etype = entry.get("type", "")
        if etype == "alert":
            alert = entry.get("alert", {})
            st.markdown(
                f"<div class='cds-log cds-log-alert'>⚠️ ALERT — "
                f"{html.escape(str(alert.get('entity_id', '')))} / "
                f"{html.escape(str(alert.get('metric', '')))} "
                f"score={alert.get('anomaly_score', 0):.2f}</div>",
                unsafe_allow_html=True,
            )
        elif etype == "response":
            text = entry.get("text", "")
            st.markdown(
                f"<div class='cds-log cds-log-detail'>🔵 {html.escape(entry.get('ts',''))} "
                f"[{html.escape(str(entry.get('entity_id','')))}]<br>"
                f"<pre style='white-space:pre-wrap;font-size:10px'>{html.escape(text[:1200])}</pre></div>",
                unsafe_allow_html=True,
            )
        st.markdown("<div class='cds-log-separator'></div>", unsafe_allow_html=True)


# ── Sidebar ────────────────────────────────────────────────────────────────────
def _render_sidebar():
    st.sidebar.markdown("## ⚙️ Controls")

    # Stream start/stop
    stopped = st.session_state.get("stream_stopped", True)
    if stopped:
        if st.sidebar.button("▶ Start Stream", use_container_width=True):
            _post_simulator_action("start")
            st.session_state.stream_stopped = False
            st.rerun()
    else:
        if st.sidebar.button("⏹ Stop Stream", use_container_width=True):
            _post_simulator_action("stop")
            st.session_state.stream_stopped = True
            st.rerun()

    st.sidebar.divider()

    # WXO agent ID override
    st.sidebar.markdown("**Supervisor Agent ID**")
    st.sidebar.text_input(
        "WO_SUPERVISOR_AGENT_ID",
        value=WO_SUPERVISOR_AGENT_ID,
        key="supervisor_agent_id_input",
        label_visibility="collapsed",
    )

    st.sidebar.divider()

    # Anomaly injection
    st.sidebar.markdown("## 💥 Inject Anomaly")
    flight_options = ["AX101", "AX202", "AX303", "AX404"]
    metric_options = SCHEDULE_METRICS

    inj_flight  = st.sidebar.selectbox("Flight",  flight_options, key="inj_flight")
    inj_metric  = st.sidebar.selectbox("Metric",  metric_options, key="inj_metric")

    # ── Per-metric context inputs ──────────────────────────────────────────────
    inj_details: dict = {}
    inj_intensity: float = 3.0

    if inj_metric == "departure_delay":
        st.sidebar.markdown(
            "**Departure delay details**  \n"
            "Enter the scheduled departure time and the new (delayed) time."
        )
        c1, c2 = st.sidebar.columns(2)
        orig_time = c1.text_input("Scheduled", value="14:30", key="dd_orig",
                                  help="Original departure time, e.g. 14:30")
        late_time = c2.text_input("Delayed",   value="15:15", key="dd_late",
                                  help="Actual/expected departure time, e.g. 15:15")
        # Compute delay in minutes from the two times; fall back to manual slider
        try:
            import datetime as _dt
            fmt = "%H:%M"
            _orig = _dt.datetime.strptime(orig_time.strip(), fmt)
            _late = _dt.datetime.strptime(late_time.strip(), fmt)
            delay_mins = max(0.0, (_late - _orig).seconds / 60.0)
        except ValueError:
            delay_mins = 0.0
        if delay_mins > 0:
            # departure_delay std = 4 min; clamp intensity 1–5
            inj_intensity = float(min(5.0, max(1.0, delay_mins / 4.0)))
            st.sidebar.caption(
                f"Delay: **{delay_mins:.0f} min** → intensity {inj_intensity:.1f}"
            )
        else:
            inj_intensity = st.sidebar.slider(
                "Intensity (manual)", 1.0, 5.0, 3.0, 0.5, key="dd_intensity"
            )
        inj_details = {
            "scheduled_departure": orig_time.strip(),
            "delayed_departure":   late_time.strip(),
            "delay_minutes":       delay_mins,
        }

    elif inj_metric == "gate_wait":
        st.sidebar.markdown(
            "**Gate wait details**  \n"
            "Enter how many extra minutes passengers are waiting beyond the normal ~5 min."
        )
        extra_wait = st.sidebar.number_input(
            "Extra wait (minutes)", min_value=1, max_value=60, value=12,
            step=1, key="gw_extra",
            help="Minutes above the normal 5-min baseline gate dwell time",
        )
        # gate_wait std = 2 min; clamp intensity 1–5
        inj_intensity = float(min(5.0, max(1.0, extra_wait / 2.0)))
        st.sidebar.caption(
            f"Extra wait: **{extra_wait} min** → intensity {inj_intensity:.1f}"
        )
        inj_details = {
            "extra_wait_minutes": int(extra_wait),
            "total_expected_wait": int(5 + extra_wait),
        }

    else:  # turnaround_time
        st.sidebar.markdown(
            "**What is a turnaround anomaly?**  \n"
            "Turnaround time is the window between a flight arriving at the gate "
            "and the same aircraft pushing back for its next departure — covering "
            "deplaning, cleaning, catering, refuelling, boarding, and paperwork. "
            "The baseline here is **~45 min** (std ±5 min).  \n\n"
            "An anomaly fires when Flink sees the rolling average spike well "
            "outside that band — e.g. a catering truck breakdown, a late inbound "
            "connection hold, or a maintenance write-up adds 20+ minutes."
        )
        inj_intensity = st.sidebar.slider(
            "Intensity", 1.0, 5.0, 3.0, 0.5, key="tt_intensity",
            help="Multiplier on the ±5 min std — intensity 3 ≈ +15 min overage",
        )
        approx_overage = int(inj_intensity * 5)
        st.sidebar.caption(
            f"Simulates ~**+{approx_overage} min** over the 45-min baseline"
        )
        inj_details = {
            "baseline_minutes":  45,
            "approx_overage_minutes": approx_overage,
        }

    col1, col2 = st.sidebar.columns(2)
    if col1.button("Inject", use_container_width=True):
        inject_anomaly(inj_flight, "schedule", inj_metric, inj_intensity, inj_details)
        st.sidebar.success(f"Injected {inj_metric} on {inj_flight}")

    if col2.button("Clear All", use_container_width=True):
        clear_all_anomalies()
        st.sidebar.info("All anomaly injections cleared.")

    # Active injections
    targets = load_anomaly_targets()
    if targets:
        st.sidebar.markdown("**Active injections:**")
        for t in targets:
            elapsed = max(0, int(time.time() - t.get("start_time", time.time())))
            d = t.get("details", {})
            if t.get("metric") == "departure_delay" and d.get("scheduled_departure"):
                detail_str = (
                    f"{d['scheduled_departure']} → {d.get('delayed_departure', '?')} "
                    f"({d.get('delay_minutes', 0):.0f} min late)"
                )
            elif t.get("metric") == "gate_wait" and d.get("extra_wait_minutes"):
                detail_str = f"+{d['extra_wait_minutes']} min extra wait"
            elif t.get("metric") == "turnaround_time" and d.get("approx_overage_minutes"):
                detail_str = f"~+{d['approx_overage_minutes']} min over baseline"
            else:
                detail_str = f"×{t.get('intensity')}"
            st.sidebar.markdown(
                f"- `{t.get('entity_id')}` / `{t.get('metric')}`  \n"
                f"  {detail_str} &nbsp; _{elapsed}s ago_"
            )

    st.sidebar.divider()

    # Reset
    if st.sidebar.button("🔄 Reset Dashboard", use_container_width=True):
        _reset_state(clear_tmp=True)
        st.rerun()


# ── Main layout ────────────────────────────────────────────────────────────────
def main():
    # Masthead
    running_label = "STREAMING" if not st.session_state.get("stream_stopped") else "PAUSED"
    pill_color = "#24a148" if running_label == "STREAMING" else "#6f6f6f"
    st.markdown(
        f"""<div class='cds-masthead'>
          <span class='cds-wordmark'>Gate Change Cascade</span>
          <span style='font-size:12px;color:#a8a8a8'>Confluent + watsonx Orchestrate</span>
          <span class='cds-status-pill' style='background:{pill_color}'>{running_label}</span>
        </div>""",
        unsafe_allow_html=True,
    )

    _render_sidebar()

    # Poll Kafka
    messages = poll_messages()
    for msg in messages:
        topic  = msg.get("_topic", "")
        ac     = msg.get("aircraft_id", "")
        metric = msg.get("metric", "")
        value  = msg.get("value")
        ts     = msg.get("timestamp", "")

        if topic == FLIGHT_EVENTS_TOPIC and ac and metric and value is not None:
            st.session_state.schedule_data[ac][metric].append({"time": ts, "value": value})
            st.session_state.readings_count += 1

        elif topic == OPS_ALERTS_TOPIC:
            st.session_state.alerts.append(msg)
            st.session_state.anomaly_count += 1
            dispatch_triage(msg)

    # Stats bar
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Readings", st.session_state.readings_count)
    col_b.metric("Anomalies Detected", st.session_state.anomaly_count)
    col_c.metric("Active Flights", len(FLIGHTS))

    # Two-column layout: charts | activity
    left, right = st.columns([3, 2], gap="medium")

    with left:
        _render_schedule_charts()
        st.divider()
        st.markdown("<h5>🛫 Flight Status</h5>", unsafe_allow_html=True)
        _render_flight_cards()

    with right:
        _render_activity_panel()

    # Auto-refresh every 3 seconds
    time.sleep(3)
    st.rerun()


if __name__ == "__main__" or True:
    main()
