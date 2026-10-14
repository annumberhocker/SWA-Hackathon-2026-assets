# Doc 09 — End-to-End Testing Guide

**Gate Change Cascade Demo**

This guide walks through three test scenarios in order of complexity. Each builds on the
previous — start with Scenario 1 to confirm the core pipeline works before adding notification
channels.

---

## Prerequisites

- All of Lab 4 (`05-wxa-agents.md`) complete: `flight_triage_agent` and `supervisor_agent` live
- Demo running: `bash app-run-local.sh` (simulator + alert consumer + dashboard all up)
- Flink anomaly detection statement in **Running** state (verify in Confluent Cloud UI or with Bob)

Verify with:
```bash
orchestrate agents list
```
Expected minimum output:
```
NAME                  DISPLAY NAME                  STATUS
supervisor_agent      Gate Change Supervisor Agent  live
flight_triage_agent   Flight Triage Agent           live
```

---

## Scenario 1 — Core Pipeline: TableFlow RAG + Triage Agent

**Tests:** Kafka → Flink anomaly detection → alert consumer → `flight_triage_agent`
(live stream window + 24h history + TableFlow Iceberg baseline + runbook RAG) →
`supervisor_agent` response → Streamlit dashboard

**No Slack, ServiceNow, or Gmail required.**

### 1.1 — Inject an anomaly

```bash
cd "$(git rev-parse --show-toplevel)/usecases/gate-change-cascade"
source .venv/bin/activate
python -m simulator.anomaly_injector AX303 schedule gate_wait --intensity 4.0
```

Or use the dashboard sidebar:
- **Flight**: `AX303`
- **Metric**: `gate_wait`
- **Intensity**: `4.0`
- Click **Inject**

### 1.2 — Wait for Flink detection (~2.5 min on first run)

The Flink job needs one full window cycle to compute the z-score. Confirm the anomaly is
detected using Bob in this chat:

```
Create and read a Flink statement that selects the latest 10 rows from ops-alerts
```

Expected: a row for `N303AX` / `gate_wait` with `anomaly_score >= 0.7`.

### 1.3 — Watch the agent pipeline

In the Streamlit dashboard at [http://localhost:8080](http://localhost:8080):

1. **Agent Activity panel** shows two rows:
   - `ALERT` — the raw ops-alerts payload (JSON)
   - `RESPONSE` — the Supervisor Agent's combined output

2. The `RESPONSE` should contain a full **Flight Triage Summary** block:

```
Flight Triage Summary

Flight: AX303  Aircraft: N303AX  Hub: DFW
Metric: gate_wait  Value: ~18 min  Score: ~0.85
Severity: HIGH  ServiceNow Urgency: 1
Live 30s: min X / max Y / avg Z minutes
24h anomaly count: N events
Historical baseline (30d): avg=12.4 min  ratio=1.45x
Runbook: §1 Option A — Immediate gate reassignment
Recommended action: Contact gate ops to reassign gate within 15 minutes
Short description for ServiceNow: "HIGH AX303 gate_wait anomaly at DFW"
```

> **Live 30s / 24h count showing N/A?** These fields require the investigator-app to be
> deployed and `INVESTIGATOR_API_URL` set in `.env`. The triage summary still works without
> it — only these two fields are affected. To enable them, complete
> [04-investigator-app.md](04-investigator-app.md) and re-run bootstrap with `--reuse-env`.

> **Historical baseline missing?** If the `Historical baseline (30d)` line shows
> "TableFlow not configured", confirm `TABLEFLOW_CATALOG_URI`, `TABLEFLOW_WAREHOUSE`, and
> `TABLEFLOW_NAMESPACE` are set in `.env` and that TableFlow status is **Syncing** in the
> Confluent Cloud UI. See [02-tableflow-setup.md](02-tableflow-setup.md) Step 2.1.

### 1.4 — Confirm the runbook RAG is being used

The **Runbook** line in the triage summary should reference a section and option from the
`flight_ops_runbook` knowledge base (e.g. `§1 Option A`). This confirms the RAG retrieval
step is working. If it reads "Runbook: N/A" the PDF was not uploaded — re-run bootstrap:

```bash
cd orchestrate
pandoc knowledge-bases/flight_ops_runbook.md -o knowledge-bases/flight_ops_runbook.pdf
bash bootstrap_env.sh --reuse-env
```

### 1.5 — Clear the injection

```bash
python -m simulator.anomaly_injector --clear
```

Wait ~3 minutes for Flink to return to baseline before running the next scenario.

---

## Scenario 2 — With ServiceNow: Automatic Incident Creation

**Additional prerequisite:** `06-servicenow-setup.md` complete and `servicenow_agent` added
as a collaborator on `supervisor_agent`.

**Tests:** Full Scenario 1 pipeline + `servicenow_agent` creating an INC in your PDI.

### 2.1 — Confirm ServiceNow agent is wired up

In the WXO UI, open `supervisor_agent` → **Collaborators** — confirm `servicenow_agent` is
listed alongside `flight_triage_agent`.

### 2.2 — Inject an anomaly (different flight to distinguish from Scenario 1)

```bash
python -m simulator.anomaly_injector AX101 schedule departure_delay --intensity 3.5
```

### 2.3 — Watch the pipeline

Wait for Flink detection as in Step 1.2, then check the dashboard `RESPONSE`.

The **Notifications** block at the bottom of the Supervisor response should now show:

```
**Notifications**
- Slack: not configured
- ServiceNow: INC0010042 created (urgency 1)
- Gmail: not configured
```

### 2.4 — Verify in ServiceNow PDI

1. Open your PDI: `https://dev<number>.service-now.com/incident_list.do`
2. Sort by **Created** descending
3. The new INC should appear with:
   - **Short description**: `HIGH AX101 departure_delay anomaly at ORD`
   - **Urgency**: 1 (High)
   - **Description**: the full Flight Triage Summary

### 2.5 — Clear the injection

```bash
python -m simulator.anomaly_injector --clear
```

---

## Scenario 3 — With Gmail: Passenger Delay Notification Email

**Additional prerequisite:** `08-gmail-setup.md` complete and the **Send email with Gmail**
tool added to `supervisor_agent` (or a dedicated email agent that `supervisor_agent`
collaborates with).

**Tests:** Full pipeline + `gmail_agent` sending a passenger-facing delay email when an anomaly
is detected.

> **What this demonstrates:** When a gate_wait or departure_delay anomaly is detected, the
> supervisor agent uses the Flight Triage Summary to compose and send a passenger notification
> email via Gmail — simulating an airline operations workflow where affected passengers receive
> proactive delay alerts.

### 3.1 — Update the supervisor agent instructions for email

The supervisor agent needs to know to send a passenger email when `gmail_agent` is available.
In the WXO UI, open `supervisor_agent` → **Instructions** and add the following to Step 2:

```
- If gmail_agent is available: compose a passenger-facing delay notification email using the
  Flight Triage Summary. Use this format:
    To: <GMAIL_RECIPIENT_ADDRESS from .env>
    Subject: Flight [flight_number] Delay Notice — [hub] [detected_at date]
    Body:
      Dear Passenger,

      We are writing to inform you that Flight [flight_number] departing from [hub] is
      currently experiencing a [metric] delay.

      Delay details:
        - Current [metric]: [value] [unit] (baseline: [avg_value_historical] [unit])
        - Severity: [severity]
        - Detected at: [detected_at]

      Our operations team is actively working on resolution.
      Recommended action: [one-sentence action from runbook]

      We apologize for the inconvenience and will provide updates as the situation develops.

      — AirX Operations
```

Save the updated instructions.

### 3.2 — Inject a departure delay anomaly

```bash
python -m simulator.anomaly_injector AX202 schedule departure_delay --intensity 5.0
```

This injects a HIGH/CRITICAL severity departure delay on AX202 (ORD→JFK), which is the most
passenger-impactful metric and produces the clearest email content.

### 3.3 — Watch the pipeline

Wait for Flink detection, then check the dashboard `RESPONSE`. The **Notifications** block
should now show:

```
**Notifications**
- Slack: not configured          (or "sent" if Slack is also configured)
- ServiceNow: not configured     (or "INC..." if ServiceNow is also configured)
- Gmail: sent to passengers@example.com
```

### 3.4 — Verify the email

Check the inbox at `GMAIL_RECIPIENT_ADDRESS`. The email should arrive within ~30 seconds and
contain:

- **Subject**: `Flight AX202 Delay Notice — ORD <today's date>`
- **Body**: passenger-facing delay message with current value, baseline ratio, severity, and
  the recommended action from the runbook

> **Tip for demos:** Use a second Gmail address as `GMAIL_RECIPIENT_ADDRESS` so you can show
> both the "ops team receives the alert" (Supervisor response on dashboard) and the
> "passenger receives the email" (inbox) side-by-side.

> **Running this for a client?** See the presenter-ready
> **[demo-script-gmail.md](demo-script-gmail.md)** — a full talk track with cues, talking
> points for each pipeline layer, and Q&A primers.

### 3.5 — Full combined test (all three channels)

If Slack, ServiceNow, and Gmail are all configured, inject a critical anomaly and observe all
channels fire simultaneously:

```bash
python -m simulator.anomaly_injector AX404 schedule turnaround_time --intensity 6.0
```

Expected end state:
- **Dashboard**: Full triage summary + all three notifications confirmed
- **Slack** `#flight-ops-alerts`: ops alert message
- **ServiceNow PDI**: new INC for `AX404 turnaround_time anomaly at DFW`
- **Email inbox**: passenger delay notification for Flight AX404

### 3.6 — Clear the injection

```bash
python -m simulator.anomaly_injector --clear
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| No `RESPONSE` in dashboard after 5 min | `WO_SUPERVISOR_AGENT_ID` not set in `.env` | Re-run `bash app-run-local.sh` after pasting the ID |
| Triage Summary `Live 30s` / `24h anomaly count` shows N/A | `INVESTIGATOR_API_URL` not set | Set `INVESTIGATOR_API_URL` in `.env` and restart `app-run-local.sh` — triage still works without it |
| Triage Summary `Historical baseline` shows "TableFlow not configured" | TableFlow vars missing or not Syncing | Confirm `TABLEFLOW_*` vars in `.env` and TableFlow status = **Syncing** (see `02-tableflow-setup.md`) |
| Triage Summary missing Runbook section | `flight_ops_runbook.pdf` not imported | Re-run bootstrap with `--reuse-env` after generating the PDF |
| ServiceNow INC not created | `servicenow_agent` not a collaborator | Add it via WXO UI → supervisor_agent → Collaborators |
| Email not received | Gmail OAuth not authorized | Re-do Step 8.8 of `08-gmail-setup.md` |
| Email received but body is wrong | Supervisor instructions not updated | Re-do Step 3.1 of this guide |
| Flink never detects anomaly | Anomaly injector not running or intensity too low | Try `--intensity 6.0`; confirm simulator is running |

---

**Return to:** [05-wxa-agents.md](05-wxa-agents.md)
