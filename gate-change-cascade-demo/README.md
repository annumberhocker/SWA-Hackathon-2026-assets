# Gate Change Cascade

**Real-time flight anomaly detection with Confluent + watsonx Orchestrate**

`Confluent Kafka` `Flink SQL` `TableFlow / Iceberg` `watsonx Orchestrate ADK`
`Multi-agent orchestration` `RAG` `ServiceNow` `Slack` `Gmail` `Confluent MCP` `WXO MCP`

---

## The Story

AeroX Airlines monitors 4 aircraft across ORD and DFW hubs in real time. When Confluent Flink
detects an anomalous spike in gate wait times, departure delays, or turnaround duration —
a **Supervisor Agent** in watsonx Orchestrate automatically:

1. **Triages** the alert using live Kafka telemetry, 30-day Iceberg historical data (TableFlow),
   and a RAG knowledge base of gate operations procedures
2. _(optional)_ **Posts** a structured notification to a Slack channel via WXO catalog
3. _(optional)_ **Opens** a ServiceNow incident with severity-mapped urgency
4. _(optional)_ **Emails** affected passengers a delay notification via Gmail

All agents are defined in code using the WXO ADK. All Confluent setup steps can be done
through the Confluent MCP server in IBM Bob.

---

## Architecture

```
Python Simulator
  └── flight-events (Kafka topic)
            │
            ├──► Flink SQL AI_DETECT_ANOMALIES (10s TUMBLE)
            │         └──► ops-alerts (Kafka topic)
            │                   └──► alert_consumer.py
            │                              └──► Supervisor Agent (WXO ADK)
            │                                       ├── Flight Triage Agent  [always]
            │                                       │     ├── flight_stream_window (live Kafka)
            │                                       │     ├── recent_flight_anomalies (24h history)
            │                                       │     ├── query_flight_history (TableFlow/Iceberg)
            │                                       │     └── flight_ops_runbook (RAG PDF)
            │                                       ├── Slack Agent (WXO catalog)  [optional]
            │                                       │     └──► #flight-ops-alerts channel
            │                                       ├── ServiceNow Agent (WXO catalog)  [optional]
            │                                       │     └──► ServiceNow PDI (INCxxxxxxx)
            │                                       └── Gmail Agent (WXO catalog)  [optional]
            │                                             └──► passenger delay notification email
            │
            └──► TableFlow (no code)
                      └──► flight-events Iceberg table (S3/GCS)
                                └──► query_flight_history tool

Streamlit Dashboard ──── Kafka Consumer ──── Agent Activity Panel
```

---

## Directory Structure

```
gate-change-cascade/
├── docs/
│   ├── 00-setup-overview.md     ← start here — credential map + pre-demo checklist
│   ├── 01-confluent-setup.md    ← Confluent Cloud + Confluent MCP (required)
│   ├── 02-tableflow-setup.md    ← TableFlow + Iceberg (required)
│   ├── 03-flink-anomaly.md      ← Flink SQL anomaly detection (required)
│   ├── 05-wxa-agents.md         ← ADK bootstrap + agent walkthrough (required)
│   ├── 06-servicenow-setup.md   ← ServiceNow PDI (optional)
│   ├── 07-slack-setup.md        ← Slack app setup (optional)
│   ├── 08-gmail-setup.md        ← Gmail passenger notifications (optional)
│   ├── 09-end-to-end-testing.md ← end-to-end test scenarios (reference)
│   └── demo-script-gmail.md     ← client demo talk track
├── simulator/
│   ├── config.py                ← flight-only config
│   ├── flight_producer.py       ← produces flight-events
│   ├── anomaly_injector.py      ← CLI anomaly injection
│   ├── alert_consumer.py        ← dispatches alerts to WXO Supervisor Agent
│   └── control_server.py        ← HTTP start/stop for dashboard
├── frontend/
│   └── app.py                   ← Streamlit dashboard
├── flink/
│   ├── 01_add_watermarks.sql
│   ├── 02_alerts_table.sql
│   └── 03_anomaly_detection_ai.sql ← AI_DETECT_ANOMALIES continuous job
├── orchestrate/
│   ├── bootstrap_env.sh         ← single script: imports all tools + agents
│   ├── agents/
│   │   ├── supervisor_agent.yaml      ← orchestrator (always imported)
│   │   └── flight_triage_agent.yaml   ← triage agent (always imported)
│   ├── connections/
│   │   ├── slack_connection.yaml      ← OAuth config (optional)
│   │   ├── servicenow_connection.yaml ← OAuth config (optional)
│   │   └── gmail_connection.yaml      ← OAuth config (optional)
│   ├── tools/
│   │   ├── flight_stream_window.py
│   │   ├── recent_flight_anomalies.py
│   │   ├── query_flight_history.py    ← PyIceberg / TableFlow
│   │   └── manifest-bundle/
│   │       └── build_manifest_db.py
│   └── knowledge-bases/
│       ├── flight_ops_runbook.md      ← source (edit here)
│       ├── flight_ops_runbook.yaml    ← ADK import definition
│       └── flight_ops_runbook.pdf     ← generated from .md (see setup)
├── app-run-local.sh
├── requirements.txt
└── .env.example
```
---
## Why use TableFlow

TableFlow is Confluent's managed pipeline that continuously syncs a Kafka topic into an Apache Iceberg table in object storage (S3/GCS/ADLS). It turns a live Kafka stream into a queryable, time-traveled analytical table - no ETL job to write or maintain.
Without TableFlow, the WXO agent can only see the live Kafka window - the last N minutes of events. With TableFlow, the agent gains a historical lens:

| Question the agent can now answer | How |
|------|------|
|"Is this gate-change rate actually unusual, or is Gate B12 always chaotic?" |Query Iceberg for the past 30-day average gate changes on this flight|
|"Has this same flight had cascading delays before?"|Full event history queryable with standard SQL|
|"What time of day does the most disruption happen?" | Aggregation over the Iceberg table, not possible on a live stream |

The demo narrative arc
1. Confluent produces `flight-events` in real time from the Python simulator.
2. Flink SQL runs the tumbling-window `AI_DETECT_ANOMALIES query` - fires when gate changes spike.
3. TableFlow (running in parallel, no extra code) continuously materializes `flight-events` → Iceberg.
4. Bridge application monitors `ops-alerts` topic and when an Anomaly lands it dispatches to the WXO agent.
5. WXO agent calls two data sources in the same conversation turn:
   - `get_flight_event_window` → real-time Kafka tail (already built)
   - `query_historical_gate_changes` → SQL over the Iceberg table 
6. Agent synthesizes: "Flight AX441 has had 4 gate changes in 22 minutes. Historically, this route averages 0.3 gate changes per hour. Opening a ServiceNow incident and notifying gate crew."
---

## Quick Start

```bash
# 1. Copy credential template — leave blank for now, fill in as you complete each setup doc
cp .env.example .env
```

Complete the setup docs in order — see [`docs/00-setup-overview.md`](docs/00-setup-overview.md)
for the full credential map and pre-demo checklist. Minimum required steps:

1. [docs/01-confluent-setup.md](docs/01-confluent-setup.md) — Confluent Cloud + Confluent MCP → fill `CONFLUENT_*` vars
2. [docs/02-tableflow-setup.md](docs/02-tableflow-setup.md) — TableFlow + Iceberg historical baseline → fill `TABLEFLOW_*` vars
3. [docs/03-flink-anomaly.md](docs/03-flink-anomaly.md) — deploy Flink anomaly detection → fill `FLINK_*` vars
4. [docs/05-wxa-agents.md](docs/05-wxa-agents.md) — ADK bootstrap + verify agents → fill `WO_*` vars

> 💡 Install the [IBM watsonx Orchestrate Agent Builder](https://marketplace.visualstudio.com/items?itemName=watson-devex.ibm-watsonx-orchestrate-agent-builder) VS Code extension before step 4 to connect your editor to WXO via MCP. See https://developer.ibm.com/tutorials/build-programmatic-agentic-workflows-watsonx-orchestrate-bob/ for steps.

Optional extensions (any order, any time after step 4):
- [docs/06-servicenow-setup.md](docs/06-servicenow-setup.md) — ServiceNow incident creation → fill `SNOW_*` vars
- [docs/07-slack-setup.md](docs/07-slack-setup.md) — Slack ops notification → fill `SLACK_*` vars
- [docs/08-gmail-setup.md](docs/08-gmail-setup.md) — Gmail passenger delay email → fill `GMAIL_*` vars

**Before a client demo:** run the [Pre-Demo Checklist](docs/00-setup-overview.md#pre-demo-checklist-run-the-morning-of-the-demo)

---

## Inject an Anomaly

```bash
# Gate wait spike on AX303 (DFW→MIA)
python -m simulator.anomaly_injector AX303 schedule gate_wait --intensity 4.0

# Departure delay spike on AX101 (ORD→LAX)
python -m simulator.anomaly_injector AX101 schedule departure_delay --intensity 5.0

# List active injections
python -m simulator.anomaly_injector --list

# Clear all
python -m simulator.anomaly_injector --clear
```

Wait ~3 minutes (ARIMA warmup on first run, ~30s on subsequent runs) then check:
- **Dashboard** Agent Activity panel for the triage summary
- _(if Slack configured)_ **Slack** `#flight-ops-alerts` for the notification
- _(if ServiceNow configured)_ **ServiceNow** `incident_list.do` for the new INC
- _(if Gmail configured)_ **Email inbox** at `GMAIL_RECIPIENT_ADDRESS` for the passenger notification

---

## Fleet Reference

| Aircraft | Type | Hub | Flight | Route |
|---|---|---|---|---|
| N101AX | B737-800 | ORD | AX101 | ORD → LAX |
| N202AX | A320neo  | ORD | AX202 | ORD → JFK |
| N303AX | B737-MAX | DFW | AX303 | DFW → MIA |
| N404AX | A321XLR  | DFW | AX404 | DFW → SEA |
