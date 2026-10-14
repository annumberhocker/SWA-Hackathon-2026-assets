# Doc 00 — Setup Overview & Pre-Demo Checklist

**Gate Change Cascade Demo — Start here**

---

## Complete Credential Map

Every variable required by this demo, where to find it, and which component uses it.

| Variable | Source | Used by | Required? |
|---|---|---|---|
| `CONFLUENT_CLUSTER_ID` | Confluent Cloud → Cluster overview → ID | Docs only | ✅ |
| `CONFLUENT_BOOTSTRAP_SERVERS` | Confluent Cloud → Cluster → Bootstrap server | Simulator, Dashboard | ✅ |
| `CONFLUENT_ENVIRONMENT_ID` | Confluent Cloud → Environment → Details → ID | MCP server, Docs | ✅ |
| `CONFLUENT_SCHEMA_REGISTRY_URL` | Confluent Cloud → Schema Registry → Endpoints | Simulator | ✅ |
| `CONFLUENT_SR_API_KEY` | Schema Registry → API keys | Simulator | ✅ |
| `CONFLUENT_SR_API_SECRET` | Schema Registry → API keys | Simulator | ✅ |
| `KAFKA_API_KEY` | Cluster → API keys → **cluster-scoped** | Simulator, Dashboard | ✅ |
| `KAFKA_API_SECRET` | Cluster → API keys → **cluster-scoped** | Simulator, Dashboard | ✅ |
| `CONFLUENT_API_KEY` | Admin → API keys → **Global** | MCP server, Flink | ✅ |
| `CONFLUENT_API_SECRET` | Admin → API keys → **Global** | MCP server, Flink | ✅ |
| `FLINK_COMPUTE_POOL_ID` | Environment → Flink → Compute pools → Pool ID | MCP server, Docs | ✅ |
| `FLINK_REST_ENDPOINT` | Environment → Flink → Endpoints → Public endpoint | MCP server | ✅ |
| `FLINK_ORG_ID` | User Settings → Organization ID | MCP server | ✅ |
| `TABLEFLOW_CATALOG_URI` | TableFlow tab → Iceberg REST endpoint | `query_flight_history` tool | ✅ |
| `TABLEFLOW_WAREHOUSE` | Your S3/GCS bucket path | `query_flight_history` tool | ✅ |
| `TABLEFLOW_NAMESPACE` | TableFlow namespace (e.g. `lkc-*****`) | `query_flight_history` tool | ✅ |
| `WO_INSTANCE` | watsonx Orchestrate → Instance URL | Alert consumer, Dashboard | ✅ |
| `WO_API_KEY` | IBM Cloud → IAM → API keys | Alert consumer, ADK bootstrap | ✅ |
| `WO_SUPERVISOR_AGENT_ID` | Written by `bootstrap_env.sh` | Alert consumer, Dashboard | ✅ |
| `WO_TRIAGE_AGENT_ID` | Written by `bootstrap_env.sh` | Reference only | ✅ |
| `WO_SLACK_AGENT_ID` | Pasted manually after catalog agent setup | Reference only | ⚪ optional |
| `WO_SNOW_AGENT_ID` | Pasted manually after catalog agent setup | Reference only | ⚪ optional |
| `WO_GMAIL_AGENT_ID` | Pasted manually after catalog agent setup | Reference only | ⚪ optional |
| `INVESTIGATOR_API_URL` | Code Engine URL — written automatically by `investigator-app/deploy/code-engine-deploy.sh` (see [04-investigator-app.md](04-investigator-app.md)) | `flight_stream_window` tool, `recent_flight_anomalies` tool, Dashboard activity panel | ⚪ optional |
| `SNOW_INSTANCE_URL` | developer.servicenow.com → Manage → Instance | ServiceNow connection | ⚪ optional |
| `SNOW_USERNAME` | `admin` (default) | ServiceNow connection | ⚪ optional |
| `SNOW_PASSWORD` | ServiceNow PDI admin password | ServiceNow connection | ⚪ optional |
| `SNOW_CLIENT_ID` | ServiceNow → OAuth Applications | ServiceNow connection | ⚪ optional |
| `SNOW_CLIENT_SECRET` | ServiceNow → OAuth Applications | ServiceNow connection | ⚪ optional |
| `SLACK_CLIENT_ID` | api.slack.com → your app → Basic Information | Slack connection | ⚪ optional |
| `SLACK_CLIENT_SECRET` | api.slack.com → your app → Basic Information | Slack connection | ⚪ optional |
| `SLACK_CHANNEL_ID` | Slack channel → View details → Channel ID | `slack_agent` | ⚪ optional |
| `GMAIL_CLIENT_ID` | Google Cloud → APIs & Services → Credentials | Gmail connection | ⚪ optional |
| `GMAIL_CLIENT_SECRET` | Google Cloud → APIs & Services → Credentials | Gmail connection | ⚪ optional |
| `GMAIL_SENDER_ADDRESS` | Your Gmail address | `gmail_agent` | ⚪ optional |
| `GMAIL_RECIPIENT_ADDRESS` | Recipient Gmail address | `gmail_agent` | ⚪ optional |
| `SIMULATOR_CONTROL_URL` | `http://localhost:8090` (default) | Dashboard | ✅ |

> **⚪ optional** means the demo pipeline runs end-to-end without that credential.
> Slack, ServiceNow, and Gmail are all optional notification channels.
> `INVESTIGATOR_API_URL` is optional but strongly recommended — without it the triage agent
> shows `N/A` for live stream and 24h anomaly count fields, and the dashboard Agent Activity
> panel falls back to a local log file. See [04-investigator-app.md](04-investigator-app.md).

---

## Setup Order

Follow the docs in this order. Steps 1, 2, 3, 4 are required. All others are optional.

| Step | Doc | Est. Time | Required? |
|---|---|---|---|
| 1 | [01-confluent-setup.md](01-confluent-setup.md) — Confluent Cloud + Confluent MCP | 20 min | ✅ |
| 2 | [02-tableflow-setup.md](02-tableflow-setup.md) — TableFlow + Iceberg | 10 min | ✅ |
| 3 | [03-flink-anomaly.md](03-flink-anomaly.md) — Flink SQL anomaly detection | 15 min | ✅ |
| 4 | [04-investigator-app.md](04-investigator-app.md) — Investigator App (Code Engine) | 10 min | ⚪ optional |
| 5 | [05-wxa-agents.md](05-wxa-agents.md) — WXO ADK bootstrap + agents | 20 min | ✅ |
| 6 | [06-servicenow-setup.md](06-servicenow-setup.md) — ServiceNow PDI | 15 min | ⚪ optional |
| 7 | [07-slack-setup.md](07-slack-setup.md) — Slack app | 10 min | ⚪ optional |
| 8 | [08-gmail-setup.md](08-gmail-setup.md) — Gmail passenger notifications | 10 min | ⚪ optional |
| 9 | [09-end-to-end-testing.md](09-end-to-end-testing.md) — End-to-end testing guide | — | ⚪ reference |

> 💡 **Tip:** Install the [IBM watsonx Orchestrate Agent Builder](https://marketplace.visualstudio.com/items?itemName=watson-devex.ibm-watsonx-orchestrate-agent-builder)
> VS Code extension before Step 4. It connects your editor to WXO via MCP so you can verify
> agents, tools, and connections without leaving VS Code. See [05-wxa-agents.md](05-wxa-agents.md)
> for setup details.

**Minimum working demo:** Steps 1, 2, 3, 5 — Confluent → TableFlow → Flink anomaly detection → WXO agents.

> **Recommended full demo:** Complete Step 4 (investigator-app) before Step 5 so that
> `INVESTIGATOR_API_URL` is in `.env` when bootstrap bakes it into the WXO tools.
> If you skip Step 4 and want to add it later, re-run `bootstrap_env.sh --reuse-env`
> after deploying the app.

---

## Pre-Demo Checklist (run the morning of the demo)

Complete these steps in order before presenting. Total time: ~15 minutes.

- [ ] **1. Verify `.env` is complete**
  ```bash
  grep -c "^[A-Z].*=$" .env  # should be 0 (no empty required vars)
  ```

- [ ] **2. Confirm Confluent topics exist**
  Prompt Bob: `List topics in my Confluent cluster`
  Expected: `flight-events` and `ops-alerts` are listed.

- [ ] **3. Start simulator — confirm flight-events is receiving messages**
  ```bash
  bash app-run-local.sh
  ```
  Open [http://localhost:8080](http://localhost:8080) → click **▶ Start Stream** → charts should populate within 5 seconds.

- [ ] **4. Confirm Flink job is Running**
  Prompt Bob: `List my Flink statements`
  Expected: `gate-change-anomaly-detection` shows status **Running**.
  If not: re-run `flink/03_anomaly_detection_ai.sql` (see [03-flink-anomaly.md](03-flink-anomaly.md)).

- [ ] **5. Confirm TableFlow is Running**
  In Confluent Cloud UI: Topics → `flight-events` → TableFlow tab → status = **Syncing**.
  If not Syncing: re-enable TableFlow (see [02-tableflow-setup.md](02-tableflow-setup.md) Step 2.1) and confirm `TABLEFLOW_*` vars are in `.env`.

- [ ] **6. Confirm all WXO agents are live**

  With WXO MCP connected, ask Bob:
  ```
  List all agents in my WXO instance
  ```
  Or use the CLI:
  ```bash
  orchestrate agents list
  ```
  Expected: `supervisor_agent` and `flight_triage_agent` listed.
  Any optional catalog agents (Slack, ServiceNow, Gmail) appear here only after being
  added as collaborators.
  If missing: run `bash orchestrate/bootstrap_env.sh --reuse-env`.

- [ ] **7. Wake up ServiceNow PDI** _(optional — skip if ServiceNow is not configured)_
  Go to [developer.servicenow.com](https://developer.servicenow.com) → **Manage** → **Instance** → **Wake Up**.
  Wait ~2 minutes for the instance to be ready.

- [ ] **8. Confirm Slack bot is in the alerts channel** _(optional — skip if Slack is not configured)_
  Open Slack → `#flight-ops-alerts` → verify the `Gate Change Cascade Alerts` bot is a member.
  If not: `/invite @Gate Change Cascade Alerts`

- [ ] **9. Inject a test anomaly and confirm the pipeline**
  ```bash
  python -m simulator.anomaly_injector AX303 schedule gate_wait --intensity 4.0
  ```
  Wait ~3 minutes (ARIMA warmup on first run), then verify:
  - Dashboard **Agent Activity** panel shows `ALERT` + `RESPONSE`
  - _(if Slack configured)_ Slack `#flight-ops-alerts` has a new message
  - _(if ServiceNow configured)_ ServiceNow `incident_list.do` has a new INC
  - _(if Gmail configured)_ Passenger delay email in `GMAIL_RECIPIENT_ADDRESS` inbox

- [ ] **10. Clear the test injection**
  ```bash
  python -m simulator.anomaly_injector --clear
  ```
  Click **🔄 Reset Dashboard** in the sidebar to clear the activity panel.

---

**Demo is ready. The next anomaly will trigger the full pipeline automatically.**
