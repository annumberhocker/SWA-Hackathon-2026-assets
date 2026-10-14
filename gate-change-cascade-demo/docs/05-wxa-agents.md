# Doc 05 — watsonx Orchestrate ADK Agents

**Gate Change Cascade Demo — Step 5**

---------

This step wires the anomaly detection pipeline into watsonx Orchestrate so that a human operator can investigate alerts through natural language. Two agents are deployed: a `flight_triage_agent` that consumes live data from the investigator app's Kafka-backed tools to answer questions about a specific flight's metrics, and a `supervisor_agent` that routes incoming anomaly alerts, coordinates triage, and optionally escalates findings via Slack, ServiceNow, or Gmail. All agents are defined in code using the WXO ADK and imported with a single bootstrap script — no WXO UI agent builder steps are required.

> **Slack, ServiceNow, and Gmail agents can also be optionally set up.** Each is set up manually from the WXO catalog —
> bootstrap does not import them. The core demo (`flight_triage_agent` + `supervisor_agent`) runs
> fully without any of them. Add any or all at any time by completing the relevant setup guides:
> [07-slack-setup.md](07-slack-setup.md), [06-servicenow-setup.md](06-servicenow-setup.md),
> [08-gmail-setup.md](08-gmail-setup.md).

---

## watsonx Orchestrate VSCode Extension (recommended)

The **IBM watsonx Orchestrate Agent Builder** extension for Visual Studio Code connects your
editor directly to your WXO instance via the MCP server built into the ADK. Once installed,
you can inspect agents, tools, and connections, run bootstrap commands, and verify the demo
state — all without leaving VS Code.

**Install the extension:**
[marketplace.visualstudio.com/items?itemName=watson-devex.ibm-watsonx-orchestrate-agent-builder](https://marketplace.visualstudio.com/items?itemName=watson-devex.ibm-watsonx-orchestrate-agent-builder)

After installing, open the extension settings and provide your `WO_INSTANCE` and `WO_API_KEY`
values. The extension launches `ibm-watsonx-orchestrate-mcp-server` in the background using
STDIO transport — the same server that powers the `watsonx-orchestrate-adk` MCP tools in Bob.
With it active you can ask VS Code Copilot (or any MCP-enabled tool in the editor) to list
agents, import tools, or verify bootstrap results alongside the code you are editing.

---

## Prerequisites

- Labs 1–4 complete (Confluent running, Flink job in Running state, investigator app deployed)
- `.env` has `WO_INSTANCE` and `WO_API_KEY` filled in
- _(Optional)_ **Slack** — complete Steps 7.1–7.4 of [07-slack-setup.md](07-slack-setup.md) to get
  `SLACK_CLIENT_ID` and `SLACK_CLIENT_SECRET` in `.env` and connection yaml files before bootstrap runs
- _(Optional)_ **ServiceNow** — complete Steps 6.1–6.4 of [06-servicenow-setup.md](06-servicenow-setup.md)
  to get `SNOW_*` vars in `.env` and connection yaml files 
- _(Optional)_ **Gmail** — complete Steps 8.1–8.4 of [08-gmail-setup.md](08-gmail-setup.md) to get
  `GMAIL_*` vars in `.env` and connection yaml files 
- `orchestrate` CLI installed in a **separate venv** (see below — it conflicts with `streamlit`):

For the ADK venv setup:
```bash
# From the gate-change-cascade directory:
python -m venv .venv-orchestrate
source .venv-orchestrate/bin/activate   # Windows: .venv-orchestrate\Scripts\activate
pip install -r requirements-orchestrate.txt
orchestrate --version
```

---

## What gets created

| Agent | How created | When |
|---|---|---|
| `flight_triage_agent` | Imported by bootstrap | ✅ always |
| `supervisor_agent` | Imported by bootstrap | ✅ always |
| `slack_agent` | **Manually from WXO catalog** — see [07-slack-setup.md](07-slack-setup.md) | ⚪ optional, any time |
| `servicenow_agent` | **Manually from WXO catalog** — see [06-servicenow-setup.md](06-servicenow-setup.md) | ⚪ optional, any time |
| `gmail_agent` | **Manually from WXO catalog** — see [08-gmail-setup.md](08-gmail-setup.md) | ⚪ optional, any time |

All three catalog agents (`slack_agent`, `servicenow_agent`, `gmail_agent`) are optional and can
be added any time after bootstrap. Complete the relevant setup guide and then add the agent as
a collaborator on `supervisor_agent` via the WXO UI.

---

## Step 4.1 — Run Bootstrap

```bash
source .venv-orchestrate/bin/activate
cd orchestrate
bash bootstrap_env.sh
```

### Prompts

Bootstrap pauses three times before registering connections:

```
Set up Slack connection? (optional) [y/N]
Set up ServiceNow connection? (optional) [y/N]
Set up Gmail connection? (optional) [y/N]
```

All three default to **N** — press Enter to skip each one. Type `y` to include:
- **Slack** requires `SLACK_CLIENT_ID` and `SLACK_CLIENT_SECRET` in `.env`
- **ServiceNow** requires `SNOW_CLIENT_ID`, `SNOW_CLIENT_SECRET`, `SNOW_USERNAME`, and `SNOW_PASSWORD` in `.env`
- **Gmail** requires `GMAIL_CLIENT_ID` and `GMAIL_CLIENT_SECRET` in `.env`

### Flags

| Flag | Effect |
|---|---|
| _(none)_ | Prompts interactively for all three connections |
| `--with-slack` / `--skip-slack` | Include or skip Slack without prompting |
| `--with-servicenow` / `--skip-servicenow` | Include or skip ServiceNow without prompting |
| `--with-gmail` / `--skip-gmail` | Include or skip Gmail without prompting |
| `-r` / `--reuse-env` | Skips `env add` — use when re-running bootstrap after the first time |

Flags can be combined:
```bash
bash bootstrap_env.sh --reuse-env --skip-servicenow --skip-gmail   # re-run, Slack only
bash bootstrap_env.sh --reuse-env --with-servicenow --with-gmail   # re-run, add both
bash bootstrap_env.sh --skip-slack --skip-servicenow --skip-gmail  # skip all connections
```

### What bootstrap does (step by step)

| Step | What happens |
|---|---|
| Configure ADK env | Creates (or reuses with `-r`) the `gate-change-cascade` ADK env and activates it against `WO_INSTANCE` |
| Slack connection | Imports `slack_connection.yaml` + sets OAuth2 credentials from `SLACK_CLIENT_ID`/`SLACK_CLIENT_SECRET` |
| ServiceNow connection | Imports `servicenow_connection.yaml` + sets OAuth password credentials — skipped if answered `n` |
| Gmail connection | Imports `gmail_connection.yaml` + sets OAuth2 `oauth_auth_code_flow` credentials from `GMAIL_CLIENT_ID`/`GMAIL_CLIENT_SECRET` — skipped if answered `n` |
| manifest SQLite | Builds `flight_manifest.sqlite` from seed data — skipped if file already exists (it is pre-built in the repo) |
| Core tools | Imports `flight_stream_window.py` and `recent_flight_anomalies.py` (both use `INVESTIGATOR_API_URL` — deployed in [04-investigator-app.md](04-investigator-app.md) first for live data), and `query_flight_history.py` |
| Knowledge base | Imports `flight_ops_runbook.pdf` as a RAG knowledge base — skipped if PDF is missing |
| Agents | Imports `flight_triage_agent` → `supervisor_agent` |
| Resolve IDs | Writes `WO_SUPERVISOR_AGENT_ID` and `WO_TRIAGE_AGENT_ID` to `.env`; prints reminders to paste catalog agent IDs manually |

### Annotated output

```
=== Configuring ADK environment 'gate-change-cascade' ===

Set up Slack connection? (optional) [y/N] n
  Skipping Slack connection.

Set up ServiceNow connection? (optional) [y/N] n
  Skipping ServiceNow connection.

Set up Gmail connection? (optional) [y/N] n
  Skipping Gmail connection.

  → flight_manifest.sqlite already present — skipping

=== Importing single-file tools ===
  import flight_stream_window.py    ← live Kafka window (requires INVESTIGATOR_API_URL=http://localhost:8081 — see docs/04-investigator-app.md)
  import recent_flight_anomalies.py ← 24h anomaly history (also uses INVESTIGATOR_API_URL)
  import query_flight_history.py    ← TableFlow / Iceberg 30-day baseline

=== Importing knowledge base ===
  → orchestrate knowledge-bases import --file flight_ops_runbook.yaml

=== Importing agents ===
  import flight_triage_agent.yaml   ← RAG + tools triage agent
  NOTE: slack_agent — optional, set up from the WXO catalog (see docs/07-slack-setup.md)
  NOTE: servicenow_agent — optional, set up from the WXO catalog (see docs/06-servicenow-setup.md)
  NOTE: gmail_agent — optional, set up from the WXO catalog (see docs/08-gmail-setup.md)
  import supervisor_agent.yaml      ← orchestrator

=== Resolving agent IDs ===
  ✓ WO_SUPERVISOR_AGENT_ID=agent-xxxxxxxx
  ✓ WO_TRIAGE_AGENT_ID=agent-xxxxxxxx
  ✗ WO_SLACK_AGENT_ID — paste manually after docs/07-slack-setup.md
  ✗ WO_SNOW_AGENT_ID  — paste manually after docs/06-servicenow-setup.md (optional)
  ✗ WO_GMAIL_AGENT_ID — paste manually after docs/08-gmail-setup.md (optional)
```

`WO_SUPERVISOR_AGENT_ID` and `WO_TRIAGE_AGENT_ID` are written to `.env` automatically.
`WO_SLACK_AGENT_ID`, `WO_SNOW_AGENT_ID`, and `WO_GMAIL_AGENT_ID` are optional — paste them manually if/when you set up those catalog agents.

> **To rebuild the manifest SQLite** (only needed if you edit the seed data in
> `orchestrate/tools/manifest-bundle/build_manifest_db.py`):
> ```bash
> bash orchestrate/tools/manifest-bundle/build.sh
> ```
> Then re-run bootstrap with `--reuse-env` to pick up the change.

> **To regenerate the runbook PDF** (only needed if you edit
> `orchestrate/knowledge-bases/flight_ops_runbook.md`):
> ```bash
> # Requires pandoc: brew install pandoc
> cd orchestrate/knowledge-bases
> pandoc flight_ops_runbook.md -o flight_ops_runbook.pdf
> ```
> Then re-run bootstrap with `--reuse-env` to re-import the knowledge base.

---

## Step 4.2 — Add the Slack Messaging Agent from the WXO Catalog _(optional)_

> Skip this step if you answered **n** to the Slack prompt during bootstrap. You can always
> come back and complete [07-slack-setup.md](07-slack-setup.md) at any time.

Once bootstrap has registered the Slack connection, add the **Slack Messaging** agent from
the WXO catalog and wire it as a collaborator:

1. In the WXO UI, go to **Agents** → **Add agent from catalog** → search for **Slack Messaging**
2. Select it, configure it, then note the agent ID shown in the URL or agent details panel
3. Paste the ID into `.env`:
   ```
   WO_SLACK_AGENT_ID=<agent-id>
   ```
4. Add `slack_agent` as a collaborator on `supervisor_agent`:
   - Open `supervisor_agent` in the WXO UI → **Collaborators** → **Add** → select the Slack agent

> See [07-slack-setup.md](07-slack-setup.md) for the full Slack app creation and OAuth credential setup.

---

## Step 4.3 — Add the ServiceNow Agent from the WXO Catalog _(optional)_

> Skip this step if you answered **n** to the ServiceNow prompt during bootstrap. You can always
> come back and complete [06-servicenow-setup.md](06-servicenow-setup.md) at any time.

Once bootstrap has registered the ServiceNow connection, add the **ServiceNow** agent from
the WXO catalog and wire it as a collaborator:

1. In the WXO UI, go to **Agents** → **Add agent from catalog** → search for **ServiceNow**
2. Select it, configure it, then note the agent ID shown in the URL or agent details panel
3. Paste the ID into `.env`:
   ```
   WO_SNOW_AGENT_ID=<agent-id>
   ```
4. Add `servicenow_agent` as a collaborator on `supervisor_agent`:
   - Open `supervisor_agent` in the WXO UI → **Collaborators** → **Add** → select the ServiceNow agent

> See [06-servicenow-setup.md](06-servicenow-setup.md) for the full ServiceNow PDI and OAuth credential setup.

---

## Step 4.4 — Add the Gmail Tool from the WXO Catalog _(optional)_

> Skip this step if you answered **n** to the Gmail prompt during bootstrap. You can always
> come back and complete [08-gmail-setup.md](08-gmail-setup.md) at any time.

Once bootstrap has registered the Gmail connection, add the **Send email with Gmail** tool
from the WXO catalog and authorize it:

1. In watsonx Orchestrate open `supervisor_agent` (or a dedicated email agent)
2. Click **Toolset** → **Add tool** → **Catalog**
3. Filter by **Tools**, search `google` under **Apps**, and select **Send email with Gmail** → **Add to Agent**
4. Click **Edit details** on the tool → **Connectors** tab → **⋮** → **Edit connection**
5. Confirm these fields are populated (bootstrap set them from your `.env`):

   | Field | Value |
   |---|---|
   | **Server URL** | `https://www.googleapis.com` |
   | **Token URL** | `https://oauth2.googleapis.com/token` |
   | **Authorization URL** | `https://accounts.google.com/o/oauth2/v2/auth` |
   | **Client ID** | your `GMAIL_CLIENT_ID` |
   | **Client Secret** | your `GMAIL_CLIENT_SECRET` |
   | **Scope** | `https://www.googleapis.com/auth/gmail.send` |
   | **Credential type** | Team credentials |

6. Click **Save Changes** → **Continue** to start the OAuth flow
7. Sign in with your Google account and grant the `gmail.send` permission

> See [08-gmail-setup.md](08-gmail-setup.md) for the full Google Cloud project and OAuth app setup.

---

## Step 4.5 — Verify Agents Are Live

```bash
orchestrate agents list -k native
```

**Expected output after bootstrap (2 agents):**
```
NAME                      DISPLAY NAME                  STATUS
supervisor_agent          Gate Change Supervisor Agent  live
flight_triage_agent       Flight Triage Agent           live
```

> `slack_agent`, `servicenow_agent`, and `gmail_agent` are all optional and created from the
> WXO catalog — they appear in the WXO UI but not in `orchestrate agents list` until added as
> collaborators on `supervisor_agent`.

---

## Step 4.6 — Quick Agent Smoke Test (optional)

Before restarting the full demo pipeline, you can send a test alert directly to the
`supervisor_agent` using Bob to confirm the agent chain is wired up correctly — no Kafka,
no Flink required.

### Sample anomaly payloads

Use one of the following JSON payloads as your test message. They match the schema written
by the `anomaly-detection-ai` Flink job into `ops-alerts-ai`.

**Gate wait spike — DFW hub (recommended first test):**
```json
{
  "entity_id": "AX303",
  "stream": "schedule",
  "metric": "gate_wait",
  "value": 18.4,
  "unit": "minutes",
  "anomaly_score": 1.0,
  "is_anomaly": true,
  "hub": "DFW",
  "detected_at": "2026-01-15T14:32:00",
  "event_time": "2026-01-15T14:31:50"
}
```

**Fuel burn anomaly — ORD hub (tests a different metric path):**
```json
{
  "entity_id": "AX101",
  "stream": "schedule",
  "metric": "fuel_burn",
  "value": 4320.7,
  "unit": "kg/hr",
  "anomaly_score": 0.97,
  "is_anomaly": true,
  "hub": "ORD",
  "detected_at": "2026-01-15T09:15:00",
  "event_time": "2026-01-15T09:14:50"
}
```

### Send with Bob

Ask Bob:
```
Chat with the supervisor_agent with this message:
{"entity_id":"AX303","stream":"schedule","metric":"gate_wait","value":18.4,"unit":"minutes","anomaly_score":1.0,"is_anomaly":true,"hub":"DFW","detected_at":"2026-01-15T14:32:00","event_time":"2026-01-15T14:31:50"}
```

Or use the MCP tool directly:
```text
mcp__watsonx-orchestrate-adk__chat_with_agent
  { "agent_name": "supervisor_agent",
    "message": "{\"entity_id\":\"AX303\",\"stream\":\"schedule\",\"metric\":\"gate_wait\",\"value\":18.4,\"unit\":\"minutes\",\"anomaly_score\":1.0,\"is_anomaly\":true,\"hub\":\"DFW\",\"detected_at\":\"2026-01-15T14:32:00\",\"event_time\":\"2026-01-15T14:31:50\"}" }
```

**Expected:** The supervisor delegates to `flight_triage_agent`, which queries the runbook
and flight history, then returns a structured response ending with
**Gate Change Cascade — Anomaly Response Complete**.

If you get an error or empty response, check:
- `orchestrate agents list` shows both agents as `live`
- `WO_SUPERVISOR_AGENT_ID` is set correctly in `.env`

---

## Step 4.7 — Restart the Demo with Agent IDs

```bash
# Stop any running demo (Ctrl+C), then:
bash app-run-local.sh
```
Then start the stream in the UI

The alert consumer now reads `WO_SUPERVISOR_AGENT_ID` from `.env` and routes every
`ops-alerts` message to the Supervisor Agent.

---

## Step 4.8 — Trigger a Test and Watch the Pipeline

### 1. Inject an anomaly

```bash
# Gate wait spike on flight AX303 at DFW
python -m simulator.anomaly_injector AX303 schedule gate_wait --intensity 4.0
```

Or use the dashboard sidebar (Flight: AX303, Metric: gate_wait → **Inject**).

### 2. Wait for Flink (~2.5 min warmup on first run)

Verify detection with Bob:
```
Create and read a Flink statement that selects the latest 10 rows from ops-alerts
```
```text
mcp__confluent__create-flink-statement
  { "statement": "SELECT * FROM `ops-alerts` LIMIT 10;",
    "statementName": "read-ops-alerts-verify" }

mcp__confluent__read-flink-statement
  { "statementName": "read-ops-alerts-verify", "timeoutInMilliseconds": 20000 }
```

### 3. Observe the agent pipeline

In the Streamlit dashboard at [http://localhost:8080](http://localhost:8080):
- **Agent Activity panel** shows: `ALERT` → `RESPONSE` from the Supervisor Agent
- The response contains the full **Gate Change Cascade — Anomaly Response Complete** summary
- _(If Slack is configured)_ A message appears in your `#flight-ops-alerts` channel
- _(If ServiceNow is configured)_ A new INC appears in your PDI: `https://dev<number>.service-now.com/incident_list.do`
- _(If Gmail is configured)_ A passenger delay notification email is sent to `GMAIL_RECIPIENT_ADDRESS`

> **For full scenario walkthroughs** (TableFlow RAG verification, ServiceNow INC validation,
> Gmail passenger email flow, and combined test), see **[09-end-to-end-testing.md](09-end-to-end-testing.md)**.

### 4. Clear the injection

```bash
python -m simulator.anomaly_injector --clear
```

---

## Adding Optional Integrations After Initial Setup

Re-run bootstrap with the relevant flag to register the connection, then follow the
corresponding numbered step above to add the catalog agent/tool to the WXO UI:

| Integration | Re-run command | UI step |
|---|---|---|
| Slack | `bash orchestrate/bootstrap_env.sh --reuse-env --with-slack` | [Step 4.2](#step-42--add-the-slack-messaging-agent-from-the-wxo-catalog-optional) |
| ServiceNow | `bash orchestrate/bootstrap_env.sh --reuse-env --with-servicenow` | [Step 4.3](#step-43--add-the-servicenow-agent-from-the-wxo-catalog-optional) |
| Gmail | `bash orchestrate/bootstrap_env.sh --reuse-env --with-gmail` | [Step 4.4](#step-44--add-the-gmail-tool-from-the-wxo-catalog-optional) |

---

## Re-running Bootstrap

If you need to re-import (e.g. after editing an agent YAML):

```bash
bash orchestrate/bootstrap_env.sh --reuse-env
```

The `--reuse-env` flag skips `env add` and goes straight to re-importing all artifacts.
