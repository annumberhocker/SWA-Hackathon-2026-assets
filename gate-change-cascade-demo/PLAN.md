# Gate Change Cascade — Full Implementation Plan
## Confluent + TableFlow + watsonx Orchestrate ADK + ServiceNow + Slack + RAG

---

## Overview

A brand-new, self-contained use case at `usecases/gate-change-cascade/` that demonstrates:

- **Confluent Kafka** streaming a single `flight-events` topic (flight-only — no baggage or maintenance topics)
- **Flink SQL** anomaly detection with `ML_DETECT_ANOMALIES` on flight schedule metrics
- **Confluent TableFlow** materializing `flight-events` into an Iceberg table for historical context
- **Confluent MCP** (Bob tool) used throughout setup instead of the Confluent Cloud UI wherever possible
- **watsonx Orchestrate ADK** used to define all agents in code — no WXO UI agent builder
- **WXO MCP** used for agent-to-agent tool routing and Slack/ServiceNow dispatch
- **Three specialized WXO agents** orchestrated by a supervisor:
  1. **Flight Triage Agent** — queries live Kafka window + historical Iceberg table + flight ops RAG knowledge base; produces a structured recommendation
  2. **Slack Notification Agent** — posts a structured summary to a Slack channel
  3. **ServiceNow Incident Agent** — opens a ServiceNow incident with full context
- **RAG** embedded in the Flight Triage Agent via a `flight_ops_runbook` knowledge base (PDF)

---

## Repository layout (new directory only)

```
usecases/gate-change-cascade/
├── PLAN.md                          ← this file
├── README.md                        ← top-level overview + architecture diagram
├── docs/
│   ├── 00-setup-overview.md         ← credential map + prerequisite checklist
│   ├── 01-confluent-setup.md        ← Confluent Cloud + MCP setup (Lab 1)
│   ├── 02-tableflow-setup.md        ← TableFlow + Iceberg setup (Lab 2)
│   ├── 03-flink-anomaly.md          ← Flink SQL anomaly detection (Lab 3)
│   ├── 04-servicenow-setup.md       ← ServiceNow PDI provisioning
│   ├── 05-slack-setup.md            ← Slack app + webhook setup
│   ├── 06-wxa-mcp-setup.md          ← WXO MCP server setup
│   └── 07-wxa-agents.md             ← ADK bootstrap + agent walkthrough (Lab 4)
├── simulator/
│   ├── __init__.py
│   ├── config.py                    ← flight-only config (no baggage/maintenance)
│   ├── flight_producer.py           ← produces flight-events only
│   ├── anomaly_injector.py          ← injects flight metric anomalies
│   ├── alert_consumer.py            ← consumes ops-alerts, dispatches to triage agent
│   └── control_server.py            ← HTTP start/stop control (unchanged pattern)
├── frontend/
│   └── app.py                       ← Streamlit dashboard (flight-only panels)
├── flink/
│   ├── 01_add_watermarks.sql        ← watermark for flight-events only
│   ├── 02_alerts_table.sql          ← ops-alerts table (same schema)
│   └── 03_anomaly_detection.sql     ← single-stream anomaly detection
├── orchestrate/
│   ├── bootstrap_env.sh             ← ADK env + imports all agents/tools/kb
│   ├── agents/
│   │   ├── supervisor_agent.yaml    ← routes alerts to triage; triage invokes Slack + ServiceNow
│   │   ├── flight_triage_agent.yaml ← live window + Iceberg history + RAG runbook
│   │   ├── slack_agent.yaml         ← posts Slack message via WXO MCP Slack tool
│   │   └── servicenow_agent.yaml    ← creates ServiceNow incident via WXO MCP tool
│   ├── tools/
│   │   ├── flight_stream_window.py        ← live Kafka window (adapted from ops_stream_window.py)
│   │   ├── query_flight_history.py        ← PyIceberg query against TableFlow Iceberg table
│   │   ├── recent_flight_anomalies.py     ← recent anomalies from ops-alerts (adapted)
│   │   ├── create_service_now_incident.py ← ported from SLB repo, airline-scoped
│   │   └── manifest-bundle/
│   │       ├── build_manifest_db.py       ← builds flight_manifest.sqlite
│   │       ├── build.sh
│   │       └── flight_manifest.sqlite     ← (git-ignored binary)
│   └── knowledge-bases/
│       ├── flight_ops_runbook.yaml        ← KB definition for ADK import
│       └── flight_ops_runbook.pdf         ← Gate change procedures + escalation guide
├── app-run-local.sh                 ← starts simulator + alert consumer + dashboard
├── requirements.txt
└── .env.example
```

---

## Sub-Tasks

---

### Sub-Task 1 — Scaffold the new directory and flight-only simulator

**Status:** `[ ] pending`

**Intent:**
Create `usecases/gate-change-cascade/` as a fully self-contained directory. Rewrite the simulator
to produce **only** `flight-events` — remove all baggage and maintenance code. The resulting simulator
is simpler and focused entirely on departure delays, gate waits, and turnaround times. All config,
profiles, and topic names for baggage and maintenance are deleted.

**Expected Outcomes:**
- Directory structure as shown in the layout above exists
- `simulator/config.py` contains only `FLIGHT_EVENTS_TOPIC`, `OPS_ALERTS_TOPIC`, `AIRCRAFT`, `FLIGHTS`,
  `GATES`, and `SCHEDULE_PROFILES` — no `BAGGAGE_PROFILES`, `MAINTENANCE_PROFILES`, no baggage/maintenance topic names
- `simulator/flight_producer.py` runs a single loop section that emits `flight-events` — no baggage or
  maintenance sections; `FLIGHT_SCHEMA_STR` is the only schema defined
- `simulator/anomaly_injector.py` only documents `schedule` stream metrics
- `simulator/alert_consumer.py` dispatches to `WO_SUPERVISOR_AGENT_ID` (new env var)
- `app-run-local.sh` starts: flight producer, alert consumer, Streamlit dashboard (three processes, same pattern as existing `lab/app/app-run-local.sh`)
- `requirements.txt` lists the same dependencies as `lab/app/requirements.txt` plus `pyiceberg`
- `.env.example` lists all required variables (see Sub-Task 7 for full list)
- `.gitignore` ignores `.env`, `.venv/`, `__pycache__/`, `manifest-bundle/*.sqlite`

**Todo List:**
- [ ] Create the full directory tree skeleton (all directories and empty placeholder files)
- [ ] Write `simulator/config.py` — copy from `lab/app/simulator/config.py` then delete
      `BAGGAGE_EVENTS_TOPIC`, `MAINTENANCE_EVENTS_TOPIC`, `BAGGAGE_PROFILES`, `MAINTENANCE_PROFILES`
      and all their references; keep `FLIGHT_EVENTS_TOPIC`, `OPS_ALERTS_TOPIC`, `AIRCRAFT`, `FLIGHTS`,
      `GATES`, `SCHEDULE_PROFILES`
- [ ] Write `simulator/flight_producer.py` — copy from `lab/app/simulator/flight_producer.py` then:
      - Remove `BAGGAGE_SCHEMA_STR` and `MAINTENANCE_SCHEMA_STR`
      - Remove `baggage_serializer` and `maint_serializer` instantiations
      - Remove sections `── 1. Aircraft maintenance telemetry` and `── 2. Baggage belt telemetry`
      - Remove `bag_drift`, `maint_drift` accumulators
      - Keep only section `── 3. Flight schedule events` (renamed to `── 1. Flight schedule events`)
      - Update docstring to reflect single-topic output
- [ ] Write `simulator/anomaly_injector.py` — copy from `lab/app/simulator/anomaly_injector.py` then:
      - Update docstring to document only `schedule` stream metrics
      - Remove baggage and maintenance examples from usage comments
- [ ] Copy `simulator/alert_consumer.py` from `lab/app/simulator/alert_consumer.py` — replace
      `WO_AIRLINE_AGENT_ID` env var with `WO_SUPERVISOR_AGENT_ID`
- [ ] Copy `simulator/control_server.py` unchanged from `lab/app/simulator/control_server.py`
- [ ] Write `simulator/__init__.py` (empty)
- [ ] Write `app-run-local.sh` — adapt from `lab/app/app-run-local.sh` with updated module paths
- [ ] Write `requirements.txt` — copy `lab/app/requirements.txt` and add `pyiceberg>=0.7.0`
- [ ] Write `.gitignore`
- [ ] Write `.env.example` (see Sub-Task 7 for the complete variable list)

**Relevant Context:**
- Source: `lab/app/simulator/flight_producer.py` — sections to keep and remove are clearly delimited
  by `── 1.`, `── 2.`, `── 3.` comments
- Source: `lab/app/simulator/config.py:60-104` — `MAINTENANCE_PROFILES` and `BAGGAGE_PROFILES` are at
  the bottom; everything above line 59 (up to `OPS_ALERTS_TOPIC`) is reused
- Source: `lab/app/app-run-local.sh` — process startup pattern to follow

---

### Sub-Task 2 — Flight-only Streamlit dashboard

**Status:** `[ ] pending`

**Intent:**
Write a simplified Streamlit dashboard that shows only flight schedule metrics (no baggage or maintenance
panels). Reuse the Carbon CSS tokens and chart rendering pattern from `lab/app/frontend/app.py` but strip
it to a single stream. The dashboard keeps the anomaly injection sidebar, the Agent Activity panel, and
the simulator start/stop control.

**Expected Outcomes:**
- `frontend/app.py` runs with `streamlit run` and shows:
  - A single **Flight Schedule** chart section with `departure_delay`, `gate_wait`, `turnaround_time` lines
    per aircraft
  - The anomaly injection sidebar (aircraft, metric, intensity, Inject / Clear buttons)
  - The Agent Activity panel (reads from investigator-api or local log)
  - The simulator start/stop button (via `SIMULATOR_CONTROL_URL`)
- No maintenance or baggage chart sections, no maintenance-specific anomaly metrics in the sidebar
- Carbon CSS design tokens retained (same `CSS` block)

**Todo List:**
- [ ] Copy `lab/app/frontend/app.py` to `frontend/app.py`
- [ ] Delete the `baggage_data` and `maint_data` session state keys and all code that reads or writes them
- [ ] Delete `MAINT_METRICS`, `MAINT_UNITS`, `BAGGAGE_METRICS`, `BAGGAGE_UNITS` constants
- [ ] Delete the `── 2. Baggage` and `── 3. Maintenance` topic subscriptions from `ALL_TOPICS`
      (keep only `FLIGHT_EVENTS_TOPIC` and `OPS_ALERTS_TOPIC`)
- [ ] Delete the maintenance and baggage chart rendering calls from the main UI loop
- [ ] Delete the aircraft maintenance status panel section
- [ ] Update the anomaly sidebar to only show `schedule` stream and its three metrics
- [ ] Update `KAFKA_CONFIG` to use `WO_SUPERVISOR_AGENT_ID` env var instead of `WO_AIRLINE_AGENT_ID`
- [ ] Update the page title and masthead to "Gate Change Cascade Demo"

**Relevant Context:**
- Source: `lab/app/frontend/app.py` — the three chart-rendering calls are near the bottom of the layout;
  the agent dispatch uses `WO_AIRLINE_AGENT_ID`
- The Agent Activity panel and investigator-api wiring are unchanged

---

### Sub-Task 3 — Flink SQL (flight-only)

**Status:** `[ ] pending`

**Intent:**
Write three Flink SQL files that target only `flight-events`. Remove the `UNION ALL` of three streams
from the existing `03_anomaly_detection.sql` — replace it with a single-stream anomaly detection query
over `flight-events`. The `ops-alerts` schema and the output format are identical to the existing
use case so the alert consumer and WXO agent tools require no changes.

**Expected Outcomes:**
- `flink/01_add_watermarks.sql` — contains only the two `ALTER TABLE` statements for `flight-events`
  (no baggage/maintenance `ALTER TABLE` statements)
- `flink/02_alerts_table.sql` — identical to `lab/flink/02_alerts_table.sql` (schema is stream-agnostic)
- `flink/03_anomaly_detection.sql` — single `INSERT INTO ops-alerts` query sourcing from `flight-events`
  only; no `windowed_maint`, `windowed_baggage`, or `UNION ALL`; the `stream` field is hardcoded to
  `'schedule'`; `ML_DETECT_ANOMALIES` ARIMA window and threshold are identical

**Todo List:**
- [ ] Write `flink/01_add_watermarks.sql`:
      - Copy Step 1a + Step 1b (`ALTER TABLE flight-events`) from `lab/flink/01_add_watermarks.sql`
      - Delete Steps 2a/2b (baggage) and 3a/3b (maintenance)
      - Keep the header comment block; update it to note only `flight-events` is needed
- [ ] Copy `flink/02_alerts_table.sql` verbatim from `lab/flink/02_alerts_table.sql` (no changes needed)
- [ ] Write `flink/03_anomaly_detection.sql`:
      - Start from `lab/flink/03_anomaly_detection.sql`
      - Replace the `windowed_maint`, `windowed_baggage`, `windowed_schedule`, `unified_windows` CTEs
        with a single `windowed_schedule` CTE over `flight-events`
      - Replace `FROM unified_windows` with `FROM windowed_schedule`
      - Hardcode `'schedule'` as the `stream` tag
      - Keep `ML_DETECT_ANOMALIES` call, `minTrainingSize=15`, and the `> 0.95` threshold filter
        exactly as in the original

**Relevant Context:**
- Source: `lab/flink/03_anomaly_detection.sql:50-62` — the `windowed_schedule` CTE is the section to keep
- The output schema of `ops-alerts` must remain identical: `entity_id`, `stream`, `metric`, `value`,
  `unit`, `anomaly_score`, `is_anomaly`, `hub`, `detected_at`, `event_time`

---

### Sub-Task 4 — Confluent MCP setup doc and TableFlow setup doc

**Status:** `[ ] pending`

**Intent:**
Write two documentation files. `docs/01-confluent-setup.md` adapts the existing `CONFLUENT_MCP_SETUP.md`
and `lab-1-confluent-streaming.md` for the flight-only topic set, with full MCP Bob prompts replacing
UI steps. `docs/02-tableflow-setup.md` is new — it documents exactly how to enable TableFlow on
`flight-events` and what Iceberg catalog values to record in `.env`.

**Expected Outcomes:**
- `docs/01-confluent-setup.md` covers:
  - Confluent Cloud environment + cluster + Schema Registry creation
  - MCP server setup in Bob (reference `CONFLUENT_MCP_SETUP.md` for Node/npm steps)
  - Topic creation via MCP: only `flight-events` and `ops-alerts`
  - `.env` variable verification table (two topics only)
  - Flink compute pool creation
- `docs/02-tableflow-setup.md` covers:
  - What TableFlow is and why it enables historical queries in this demo
  - Step-by-step: Topics → `flight-events` → TableFlow tab → Enable → choose S3/GCS bucket
  - How to record `TABLEFLOW_CATALOG_URI`, `TABLEFLOW_WAREHOUSE`, `TABLEFLOW_NAMESPACE` in `.env`
  - How to verify data is landing (object store file count after 2 min)
  - Note that `query_flight_history.py` gracefully skips the Iceberg query and returns
    `status: tableflow_not_configured` if these vars are blank — so the demo works without TableFlow
    for dry runs

**Todo List:**
- [ ] Write `docs/01-confluent-setup.md`:
      - Adapt the topic list from three to two (`flight-events`, `ops-alerts`)
      - Include full Bob MCP prompt + tool call block for topic creation
      - Include full Bob MCP prompt + tool call block for schema inspection after simulator starts
      - Include full Bob MCP prompt + tool call block for running each Flink SQL statement
      - Include troubleshooting table from `lab-1-confluent-streaming.md` scoped to flight-only
- [ ] Write `docs/02-tableflow-setup.md`:
      - Include UI screenshots path labels (not actual images, just `<!-- screenshot: ... -->` markers)
      - Include the exact `.env` variables to populate
      - Include a Bob MCP prompt to verify topic messages are flowing before enabling TableFlow

**Relevant Context:**
- Source: `lab/CONFLUENT_MCP_SETUP.md` — MCP config JSON block and variable table to adapt
- Source: `lab/lab-1-confluent-streaming.md` — Bob prompt/tool call patterns to follow exactly
- TableFlow is configured at: `config.yaml:145-152` — auth already scaffolded

---

### Sub-Task 5 — WXO ADK agent tools

**Status:** `[ ] pending`

**Intent:**
Write four Python tool files for the WXO agents. All four use the `@tool` decorator from
`ibm_watsonx_orchestrate`. Tools 1–2 are adapted from existing airline-ops tools. Tool 3 is new
(PyIceberg TableFlow query). Tool 4 is ported from the SLB ServiceNow repo with airline-specific
field simplification.

A fifth tool — Slack message posting — is **not** written as a Python file. It is provided by the
**WXO MCP server** (ibm-orchestrate-mcp) which exposes a native Slack tool that the Slack agent
calls. This demonstrates WXO MCP usage as requested.

**Expected Outcomes:**
- `orchestrate/tools/flight_stream_window.py` — adapted from `lab/orchestrate/tools/ops_stream_window.py`;
  returns live 30-second window for `flight-events` stream; env var `INVESTIGATOR_API_URL` injected
  at bootstrap time
- `orchestrate/tools/recent_flight_anomalies.py` — adapted from
  `lab/orchestrate/tools/recent_ops_anomalies.py`; filters to `stream='schedule'` by default
- `orchestrate/tools/query_flight_history.py` — new PyIceberg tool:
  - Reads `TABLEFLOW_CATALOG_URI`, `TABLEFLOW_WAREHOUSE`, `TABLEFLOW_NAMESPACE` from environment
  - Loads the `flight-events` Iceberg table, scans last 30 days, filters `metric = 'gate_wait'`
  - Returns: `avg_gate_wait_30d`, `p95_gate_wait_30d`, `current_rate_vs_historical` (ratio),
    `sample_recent_events` (last 5 rows)
  - On missing env vars returns `{"status": "tableflow_not_configured"}` — graceful degradation
- `orchestrate/tools/create_service_now_incident.py` — ported from SLB repo:
  - Connection name: `service-now`
  - Pydantic model renamed `AirlineIncident`; keeps only: `number`, `short_description`,
    `priority`, `urgency`, `opened_at`, `state`
  - Removes all Maximo-specific fields (`u_application`, `u_classification`, `u_mttr`, etc.)
- `orchestrate/tools/manifest-bundle/build_manifest_db.py` + `build.sh` — creates
  `flight_manifest.sqlite` with `flights` and `gate_changes` tables, seeded for the 4 demo aircraft

**Todo List:**
- [ ] Write `orchestrate/tools/flight_stream_window.py`:
      - Copy `lab/orchestrate/tools/ops_stream_window.py`
      - Rename function to `flight_stream_window`
      - Update description to reference `flight-events` stream and `schedule` metrics
      - Keep `INVESTIGATOR_API_URL` injection pattern unchanged
- [ ] Write `orchestrate/tools/recent_flight_anomalies.py`:
      - Copy `lab/orchestrate/tools/recent_ops_anomalies.py`
      - Rename function to `recent_flight_anomalies`
      - Add `stream: str = "schedule"` default param to always filter to schedule stream
- [ ] Write `orchestrate/tools/query_flight_history.py`:
      - `@tool` decorator with clear description mentioning "TableFlow Iceberg historical data"
      - Accept `flight_number: str`, `metric: str = "gate_wait"`, `days: int = 30`
      - Use `pyiceberg.catalog.load_catalog` with REST catalog config from env vars
      - Scan with filter `(pc.field("flight_number") == flight_number) & (pc.field("metric") == metric)`
      - Return aggregated stats dict; wrap all pyiceberg calls in try/except
- [ ] Write `orchestrate/tools/create_service_now_incident.py`:
      - Port from `Schlumberger-SLB-Maximo-ServiceNow-Ticket-Agent/tools/create_service_now_incident.py`
      - Remove fields: `application`, `classification`, `type`, `agent_status`, `geo_unit`, `parent`,
        `parent2`, `business_view`, `internal_id`, `external_vendor_ticket`, `mttr`, `division`
      - Rename `MaximoIncident` → `AirlineIncident`
      - Keep: `number`, `short_description`, `priority`, `urgency`, `opened_at`, `state`
      - Keep `CONNECTION_SNOW = 'service-now'` and `connections.basic_auth` pattern unchanged
- [ ] Write `orchestrate/tools/manifest-bundle/build_manifest_db.py`:
      - Creates `flights` table: `flight_number`, `aircraft_id`, `origin`, `destination`,
        `passenger_count`, `aircraft_type`, `hub`
      - Creates `gate_changes` table: `flight_number`, `changed_at`, `from_gate`, `to_gate`, `reason`
      - Seeds 4 flights (AX101, AX202, AX303, AX404) and ~60 historical gate change records
- [ ] Write `orchestrate/tools/manifest-bundle/build.sh`
- [ ] Add `manifest-bundle/flight_manifest.sqlite` to `.gitignore`

**Relevant Context:**
- Source tools: `lab/orchestrate/tools/ops_stream_window.py`, `recent_ops_anomalies.py`,
  `ops_history_lookup.py` — copy-adapt pattern
- Source ServiceNow: `Schlumberger-SLB-Maximo-ServiceNow-Ticket-Agent/tools/create_service_now_incident.py`
- PyIceberg catalog init: `pyiceberg.catalog.load_catalog("default", **{"uri": CATALOG_URI, "warehouse": WAREHOUSE})`

---

### Sub-Task 6 — WXO ADK agents (YAML + bootstrap script)

**Status:** `[ ] pending`

**Intent:**
Write four agent YAML files and the `bootstrap_env.sh` script that imports them all using the WXO ADK
CLI. All agents are defined in code — no WXO UI agent builder is used.

**Agent topology:**
```
ops-alerts (Kafka)
    └── alert_consumer.py → POST alert payload →
            Supervisor Agent
                └── delegates to → Flight Triage Agent
                                        ├── flight_stream_window (tool)
                                        ├── recent_flight_anomalies (tool)
                                        ├── query_flight_history (PyIceberg/TableFlow tool)
                                        └── flight_ops_runbook (RAG knowledge base)
                                    ← returns structured triage summary →
                └── delegates to → Slack Notification Agent
                                        └── (WXO MCP Slack tool)
                └── delegates to → ServiceNow Incident Agent
                                        └── create_service_now_incident (tool)
```

**Expected Outcomes:**
- `orchestrate/agents/supervisor_agent.yaml` — `style: react`; instructs the agent to:
  1. Pass the alert payload to `flight_triage_agent` and capture the structured summary
  2. Pass the summary to `slack_agent` for notification
  3. Pass the summary to `servicenow_agent` to open an incident
  4. Return a combined confirmation: triage summary + SNow incident number + Slack confirmation
  - Lists `flight_triage_agent`, `slack_agent`, `servicenow_agent` as collaborators
- `orchestrate/agents/flight_triage_agent.yaml` — `style: default`; deterministic 8-step instructions:
  1. Extract alert fields
  2. Map anomaly_score to severity
  3. Call `flight_stream_window` (live 30s pulse)
  4. Call `recent_flight_anomalies` (24h frequency)
  5. Call `query_flight_history` (TableFlow 30-day baseline; handle `tableflow_not_configured`)
  6. Retrieve matching `flight_ops_runbook` section
  7. Compose structured triage summary (defined output schema)
  8. Return summary and stop — do not send notifications (supervisor handles that)
  - Tools: `flight_stream_window`, `recent_flight_anomalies`, `query_flight_history`
  - Knowledge base: `flight_ops_runbook`
- `orchestrate/agents/slack_agent.yaml` — `style: react`; receives a pre-composed summary string;
  calls the WXO MCP Slack tool (`post_message`) with `channel = SLACK_CHANNEL_ID` from env;
  returns `{"status": "sent", "channel": ..., "ts": ...}`
  - Tools: WXO MCP `slack_post_message` (registered via WXO MCP connection)
- `orchestrate/agents/servicenow_agent.yaml` — `style: react`; receives the triage summary;
  constructs `short_description` and `description` from it; calls `create_service_now_incident`;
  returns the incident number
  - Tools: `create_service_now_incident`
- `orchestrate/bootstrap_env.sh` — follows the exact pattern of `lab/orchestrate/bootstrap_env.sh`:
  - Creates/activates `gate-change-cascade` ADK env
  - Builds `manifest-bundle/flight_manifest.sqlite` if not present
  - Stages tools with `INVESTIGATOR_API_URL` baked in
  - Imports tools: `flight_stream_window`, `recent_flight_anomalies`, `query_flight_history`,
    `create_service_now_incident` (multi-file bundle for manifest sqlite)
  - Imports knowledge base: `flight_ops_runbook` from `knowledge-bases/flight_ops_runbook.pdf`
  - Imports agents in dependency order: `flight_triage_agent` → `slack_agent` → `servicenow_agent`
    → `supervisor_agent`
  - Resolves all four agent IDs with `jq` and writes them to `.env`:
    `WO_SUPERVISOR_AGENT_ID`, `WO_TRIAGE_AGENT_ID`, `WO_SLACK_AGENT_ID`, `WO_SNOW_AGENT_ID`

**Todo List:**
- [ ] Write `orchestrate/agents/flight_triage_agent.yaml`:
      - Model `airline_ops_agent.yaml` structure exactly (same spec_version, kind, style fields)
      - Write 8-step deterministic instructions
      - Reference `flight_ops_runbook` knowledge base for gate change escalation procedures
      - Include graceful handling of `status: tableflow_not_configured` in step 5
- [ ] Write `orchestrate/agents/slack_agent.yaml`:
      - Instructions: receive structured summary, call Slack tool, return confirmation
      - Document the WXO MCP Slack tool name and expected params
- [ ] Write `orchestrate/agents/servicenow_agent.yaml`:
      - Instructions: receive structured summary, derive urgency from severity, call `create_service_now_incident`
      - Urgency mapping: CRITICAL/HIGH → 1, MEDIUM → 2, LOW → 3
- [ ] Write `orchestrate/agents/supervisor_agent.yaml`:
      - Style `react`; collaborators: `flight_triage_agent`, `slack_agent`, `servicenow_agent`
      - Sequential orchestration instructions
- [ ] Write `orchestrate/bootstrap_env.sh`:
      - Follow `lab/orchestrate/bootstrap_env.sh` exactly for structure and error handling
      - Update artifact names, env var names, and import order
      - Add WXO MCP connection registration step for Slack (using `orchestrate connections add`)
      - Add ServiceNow connection registration step
      - Write all four agent IDs to `.env`

**Relevant Context:**
- Source agent YAML: `lab/orchestrate/agents/airline_ops_agent.yaml` — follow structure verbatim
- Source bootstrap: `lab/orchestrate/bootstrap_env.sh` — follow error handling, env logic, and
  `upsert_env` function exactly
- WXO MCP Slack tool is registered as a connection in WXO, not as a Python file

---

### Sub-Task 7 — Knowledge base: `flight_ops_runbook`

**Status:** `[ ] pending`

**Intent:**
Create a Flight Operations Runbook that the `flight_triage_agent` uses as a RAG knowledge base.
This is the RAG component of the demo. The runbook covers gate change escalation procedures,
delay notification SLAs, and turnaround anomaly response — organized in sections the agent
instructions explicitly reference. The runbook is authored as a structured Markdown file, then
converted to PDF for ADK import.

**Expected Outcomes:**
- `orchestrate/knowledge-bases/flight_ops_runbook.md` — authored content; serves as the source
- `orchestrate/knowledge-bases/flight_ops_runbook.pdf` — PDF rendition imported into WXO
- `orchestrate/knowledge-bases/flight_ops_runbook.yaml` — ADK knowledge base definition
- Runbook contains at minimum:
  - §1 — Gate Change Anomalies: thresholds, immediate actions, escalation path, ServiceNow urgency
    mapping
  - §2 — Departure Delay Anomalies: delay buckets (15–30 min / 30–60 min / 60+ min), crew
    notification chain, passenger rebooking trigger
  - §3 — Turnaround Time Anomalies: root cause checklist, ground crew coordination, tarmac
    delay regulation reference
  - §4 — Fleet Reference: aircraft types, hub assignments, operations contacts per hub

**Todo List:**
- [ ] Write `orchestrate/knowledge-bases/flight_ops_runbook.md` with the four sections above;
      each section should have at least one "Option A / Option B / Option C" decision block
      that the triage agent's instructions reference by section number (e.g. §1 Option A)
- [ ] Convert to PDF — use `pandoc flight_ops_runbook.md -o flight_ops_runbook.pdf` or any
      Markdown→PDF converter; document the conversion command in `docs/07-wxa-agents.md`
- [ ] Write `orchestrate/knowledge-bases/flight_ops_runbook.yaml`:
      ```yaml
      name: flight_ops_runbook
      display_name: Flight Operations Runbook
      description: >
        Gate change, departure delay, and turnaround anomaly procedures
        for the Gate Change Cascade demo. Reference: GCC-2024 Rev 1.0.
      files:
        - flight_ops_runbook.pdf
      ```

**Relevant Context:**
- Source: `lab/orchestrate/knowledge-bases/airline_ops_runbook.yaml` — follow this structure
- The triage agent instructions in Sub-Task 6 must reference section numbers that match what
  is written in this runbook

---

### Sub-Task 8 — ServiceNow + Slack setup docs

**Status:** `[ ] pending`

**Intent:**
Write the two external-system setup guides. These are the most manual parts of the demo and need
clear, step-by-step instructions so a demo presenter can set them up before a client session.

**Expected Outcomes:**
- `docs/04-servicenow-setup.md` — complete guide to:
  - Provisioning a ServiceNow PDI (reference to SLB repo `README_SERVICENOW_SETUP.md`)
  - Registering the `service-now` WXO connection via `orchestrate connections add`
  - Verifying `create_service_now_incident` works by running the tool from the ADK CLI
- `docs/05-slack-setup.md` — complete guide to:
  - Creating a Slack App at api.slack.com with `chat:write` scope
  - Getting a Bot User OAuth Token
  - Getting the Channel ID for the alerts channel
  - Registering the Slack connection in WXO via `orchestrate connections add --type slack`
  - Verifying the Slack agent can post a test message via the ADK CLI

**Todo List:**
- [ ] Write `docs/04-servicenow-setup.md`:
      - Link to `Schlumberger-SLB-Maximo-ServiceNow-Ticket-Agent/scripts/README_SERVICENOW_SETUP.md`
        for PDI provisioning steps (do not duplicate)
      - Document the exact `orchestrate connections add` command for ServiceNow:
        `orchestrate connections add -a service-now --type basic_auth --url <PDI_URL> -u admin -p <password>`
      - Document `.env` variables: `SNOW_INSTANCE_URL`, `SNOW_USERNAME`, `SNOW_PASSWORD`
- [ ] Write `docs/05-slack-setup.md`:
      - Step-by-step: api.slack.com → Create App → OAuth & Permissions → `chat:write` → Install to workspace
      - Step to find Channel ID (right-click channel → View channel details → bottom of About tab)
      - `orchestrate connections add` command for Slack
      - Document `.env` variables: `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`

**Relevant Context:**
- `Schlumberger-SLB-Maximo-ServiceNow-Ticket-Agent/scripts/README_SERVICENOW_SETUP.md` — reference, not duplicate
- WXO MCP Slack integration uses `ibm-orchestrate-mcp` which is documented in WXO product docs

---

### Sub-Task 9 — WXO MCP setup doc + full end-to-end README

**Status:** `[ ] pending`

**Intent:**
Write the WXO MCP setup guide and the top-level README that ties everything together. The README
is the first file a new demo presenter reads — it must be self-contained with an architecture
diagram reference, prerequisites, and a 10-step "quick demo path."

**Expected Outcomes:**
- `docs/06-wxa-mcp-setup.md` — covers how to register the WXO MCP server in Bob and how
  the WXO MCP Slack tool is surfaced to the `slack_agent`
- `docs/07-wxa-agents.md` — covers the full ADK bootstrap flow with annotated command output,
  how to verify each agent is live, how to trigger a test alert, and how to read the agent trace
- `README.md` — top-level overview including:
  - Story narrative (2–3 sentences)
  - Architecture text diagram
  - Prerequisites table (with links to each doc)
  - 10-step quick demo path (start simulator → inject anomaly → ServiceNow + Slack)
  - Directory structure overview

**Todo List:**
- [ ] Write `docs/06-wxa-mcp-setup.md`
- [ ] Write `docs/07-wxa-agents.md`:
      - `bootstrap_env.sh` walkthrough with expected console output at each step
      - How to verify all four agents are live: `orchestrate agents list`
      - How to trigger a test: `python -m simulator.anomaly_injector AX101 schedule gate_wait --intensity 4.0`
      - How to confirm: Slack message received + ServiceNow INC created + dashboard Agent Activity panel
      - Pandoc command to regenerate the runbook PDF if the Markdown is edited
- [ ] Write `docs/00-setup-overview.md` — credential map table (all 20+ env vars, where to find each)
- [ ] Write `README.md`

**Relevant Context:**
- `lab/README.md` — follow narrative and architecture diagram style
- `lab/lab-2-wxo-agent.md` — follow the ADK bootstrap walkthrough format

---

### Sub-Task 10 — End-to-end smoke test checklist

**Status:** `[ ] pending`

**Intent:**
Document a step-by-step pre-demo verification checklist that can be run in ~15 minutes the morning
before a client demo. This becomes `docs/00-setup-overview.md`'s final section.

**Expected Outcomes:**
- A numbered checklist in `docs/00-setup-overview.md` that verifies:
  1. `.env` has all required variables filled in
  2. `flight-events` and `ops-alerts` topics exist in Confluent
  3. Simulator starts and `flight-events` receives messages (visible in Confluent UI Topics → Messages)
  4. Flink job `gate-change-anomaly-detection` is in Running state
  5. TableFlow shows "Running" status for `flight-events` (or confirmed skipped for dry run)
  6. `bootstrap_env.sh` has been run and all four WXO agent IDs are in `.env`
  7. ServiceNow PDI is awake (developer.servicenow.com → Manage → Instance → Wakeup)
  8. Slack app is installed in the workspace and bot is in the alerts channel
  9. Inject a test anomaly → confirm Slack message arrives → confirm ServiceNow INC is created
  10. Clear the test anomaly: `python -m simulator.anomaly_injector --clear`

---

## `.env.example` — Complete Variable Reference

```env
# ── Confluent Cloud ──────────────────────────────────────────────────────────
CONFLUENT_CLUSTER_ID=
CONFLUENT_BOOTSTRAP_SERVERS=
CONFLUENT_ENVIRONMENT_ID=
CONFLUENT_SCHEMA_REGISTRY_URL=
CONFLUENT_SR_API_KEY=
CONFLUENT_SR_API_SECRET=
KAFKA_API_KEY=
KAFKA_API_SECRET=
CONFLUENT_API_KEY=
CONFLUENT_API_SECRET=

# ── Confluent Flink ──────────────────────────────────────────────────────────
FLINK_COMPUTE_POOL_ID=
FLINK_REST_ENDPOINT=
FLINK_ORG_ID=

# ── Confluent TableFlow (Iceberg) ────────────────────────────────────────────
TABLEFLOW_CATALOG_URI=
TABLEFLOW_WAREHOUSE=
TABLEFLOW_NAMESPACE=

# ── watsonx Orchestrate ──────────────────────────────────────────────────────
WO_INSTANCE=
WO_API_KEY=
WO_SUPERVISOR_AGENT_ID=       # written by bootstrap_env.sh
WO_TRIAGE_AGENT_ID=           # written by bootstrap_env.sh
WO_SLACK_AGENT_ID=            # written by bootstrap_env.sh
WO_SNOW_AGENT_ID=             # written by bootstrap_env.sh

# ── Investigator API (instructor-deployed, optional for dry runs) ────────────
INVESTIGATOR_API_URL=

# ── ServiceNow ───────────────────────────────────────────────────────────────
SNOW_INSTANCE_URL=
SNOW_USERNAME=admin
SNOW_PASSWORD=

# ── Slack ────────────────────────────────────────────────────────────────────
SLACK_BOT_TOKEN=
SLACK_CHANNEL_ID=

# ── Simulator control ────────────────────────────────────────────────────────
SIMULATOR_CONTROL_URL=http://localhost:8090
```

---

## Files Reused Unchanged

| Source file | Destination | Note |
|---|---|---|
| `lab/app/simulator/control_server.py` | `simulator/control_server.py` | Copy verbatim |
| `lab/flink/02_alerts_table.sql` | `flink/02_alerts_table.sql` | Copy verbatim |
| `lab/orchestrate/bootstrap_env.sh` | `orchestrate/bootstrap_env.sh` | Adapt only env name and artifact names |

## Files Deleted (not carried forward)

| File removed | Reason |
|---|---|
| All baggage topic/schema/profile code | Scope reduced to flight-only |
| All maintenance topic/schema/profile code | Scope reduced to flight-only |
| `ops_history_lookup.py` + `airline_history.sqlite` | Replaced by `query_flight_history.py` + `manifest-bundle/flight_manifest.sqlite` |
| `airline_ops_agent.yaml` | Replaced by four-agent topology |
| `airline_ops_runbook.yaml/.pdf` | Replaced by `flight_ops_runbook.yaml/.pdf` |
