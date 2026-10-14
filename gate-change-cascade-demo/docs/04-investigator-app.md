# Doc 04 — Investigator App

**Gate Change Cascade Demo — Step 4**

-----------
The investigator-app is a lightweight FastAPI service that provides three capabilities
the WXO tools and dashboard cannot do reliably on their own:

1. **Live stream window** — tails `flight-events` in real time so the triage agent can
   report min/max/avg for the last 30 seconds at the moment of anomaly detection
2. **24h anomaly history** — tails `ops-alerts` so the agent can report how many times
   this flight/metric has triggered anomalies today
3. **Shared activity log** — a cross-process in-memory log the dashboard Agent Activity
   panel reads from, so it works regardless of network connectivity between your laptop
   and the Kafka brokers

Without it the triage summary shows `N/A` for the live stream and 24h count fields,
and the dashboard Agent Activity panel falls back to a local log file.

> ⚠️ **External deployment is required for the WXO tools to work.**
> The `flight_stream_window` and `recent_flight_anomalies` tools run inside the WXO
> agent on IBM Cloud — they call `INVESTIGATOR_API_URL` outbound from IBM's
> infrastructure. A `localhost` URL is not reachable from there.

> **Skip this step if you are doing a quick dry run.** The core triage pipeline
> (Flink → supervisor → triage → runbook + TableFlow) works fully without the
> investigator-app — the live stream and 24h count fields will show `N/A`.
> Come back to this step when you want the full live data experience.

---

## Prerequisites

- **Podman** (or Docker) installed and running locally — used to build the image
- **IBM Cloud account** with Code Engine and Container Registry access
- `ibmcloud` CLI with the Container Registry and Code Engine plugins:
  ```bash
  ibmcloud plugin install container-registry code-engine -r 'IBM Cloud'
  ```
- Confluent credentials already in `.env` (done in Lab 1)

---

## Step 4.1 — Configure the deploy environment

```bash
cp investigator-app/deploy/.env.example investigator-app/deploy/.env
```

Open `investigator-app/deploy/.env` and fill in:

```
WO_API_KEY=<your IBM Cloud API key>
RESOURCE_GROUP=<your TechZone resource group name>
REGION=ca-tor
```

The ICR namespace defaults to `gcc-investigator` and is created automatically
if it doesn't exist — you do not need to set `ICR_NAMESPACE` unless you want
a different name.

The `WO_API_KEY` is reused as the ICR registry secret password — no separate
registry account or token is needed.

Confluent credentials are read automatically from `.env` — no duplication needed.

---

## Step 4.2 — Deploy to Code Engine

```bash
bash investigator-app/deploy/code-engine-deploy.sh
```

The script will:
1. Log in to IBM Cloud and ensure the ICR namespace exists
2. Build the image locally with Podman (falls back to Docker), tagged for the correct regional ICR host (`ca.icr.io`, `us.icr.io`, etc. — derived from `REGION`)
3. Log in to ICR and push the image
4. Select (or create) the Code Engine project
5. Register the ICR credentials as a CE registry secret (username `iamapikey`, password from `WO_API_KEY`)
6. Deploy `gcc-investigator` with `--min-scale 1` (always warm — no cold starts)
7. Print the public URL and write `INVESTIGATOR_API_URL` to both `deploy/.env` and `.env`

### Expected output

```
╔════════════════════════════════════════════════════════════╗
║   IBM Code Engine — Gate Change Cascade Investigator API   ║
╚════════════════════════════════════════════════════════════╝

  Image:   ca.icr.io/<namespace>/gcc-investigator:latest
  Region:  ca-tor
  Project: ce-<resource-group>

✓ Already logged in to IBM Cloud
✓ ICR namespace ready
✓ Image built: ca.icr.io/<namespace>/gcc-investigator:latest
✓ Image pushed: ca.icr.io/<namespace>/gcc-investigator:latest
✓ Project selected
✓ Registry secret ready
  Deploying to Code Engine…
  ✓ Application live

╔════════════════════════════════════════════════════════════╗
║                    Deployment Complete!                    ║
╚════════════════════════════════════════════════════════════╝

┌─ gcc-investigator ─────────────────────────────────────────┐
  URL:    https://gcc-investigator.<hash>.ca-tor.codeengine.appdomain.cloud
  Health: https://gcc-investigator.<hash>.ca-tor.codeengine.appdomain.cloud/healthz
  Docs:   https://gcc-investigator.<hash>.ca-tor.codeengine.appdomain.cloud/docs
└────────────────────────────────────────────────────────────┘
```

`INVESTIGATOR_API_URL` is written to `.env` automatically.

---

## Step 4.3 — Verify

```bash
curl $(grep ^INVESTIGATOR_API_URL .env | cut -d= -f2)/healthz
# {"status":"ok","kafka_configured":true}
```

The FastAPI interactive docs are at `<url>/docs`.

---

## Step 4.4 — Re-run bootstrap with the URL baked in

The two WXO tools (`flight_stream_window` and `recent_flight_anomalies`) have
`INVESTIGATOR_API_URL` baked in at import time by `bootstrap_env.sh`. Now that the
URL is in `.env`, re-run bootstrap to re-import them with the correct value:

```bash
source .venv-orchestrate/bin/activate
cd orchestrate
bash bootstrap_env.sh --reuse-env
```

The tools will now return live data instead of `N/A`.

---

## Architecture

```
Code Engine (always-on, 1 instance)
└── FastAPI app (investigator/main.py)
    ├── /stream_window    — ephemeral Kafka consumer, tails flight-events
    ├── /recent_anomalies — ephemeral Kafka consumer, tails ops-alerts
    └── /agent_activity   — in-memory deque (maxlen=2000), resets on restart

Confluent Cloud
├── flight-events   ← read by /stream_window
└── ops-alerts      ← read by /recent_anomalies
```

The service holds no state on disk. The activity log resets on container restart.
`--min-scale 1` keeps one instance always warm so there are no cold-start delays
when the triage agent calls the tools.

---

**Next:** [05-wxa-agents.md](05-wxa-agents.md) — WXO ADK bootstrap + agents
