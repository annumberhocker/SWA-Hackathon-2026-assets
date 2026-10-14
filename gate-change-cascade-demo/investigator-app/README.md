# Investigator App — Gate Change Cascade

A lightweight FastAPI service that gives the WXO triage agent and dashboard live data
they cannot reliably get from long-lived Kafka connections.

> ⚠️ **External deployment is required for the WXO tools to work.**
> `flight_stream_window` and `recent_flight_anomalies` run inside the WXO agent on IBM Cloud
> and call `INVESTIGATOR_API_URL` outbound from IBM's infrastructure — a `localhost` URL
> is unreachable from there. Deploy to Code Engine (or any public HTTPS endpoint).

## Endpoints

| Endpoint | Used by | Purpose |
|---|---|---|
| `GET /stream_window` | `flight_stream_window` WXO tool | 30-second rolling window of `flight-events` — min/max/avg per aircraft at anomaly time |
| `GET /recent_anomalies` | `recent_flight_anomalies` WXO tool | 24-hour tail of `ops-alerts` — gives the agent pattern context ("3rd gate_wait anomaly today") |
| `POST/GET/DELETE /agent_activity` | Dashboard, alert consumer | Shared in-memory activity log so the Agent Activity panel works across process restarts |

Without this service `flight_stream_window` and `recent_flight_anomalies` return `N/A`,
and the dashboard Agent Activity panel falls back to a local log file.

## Deploy (IBM Code Engine)

See **[docs/04-investigator-app.md](../docs/04-investigator-app.md)** for full steps.
The short version:

```bash
# From gate-change-cascade/
cp investigator-app/deploy/.env.example investigator-app/deploy/.env
# Edit deploy/.env: set WO_API_KEY and RESOURCE_GROUP
bash investigator-app/deploy/code-engine-deploy.sh
```

`INVESTIGATOR_API_URL` is written to `.env` automatically. Then re-run bootstrap:

```bash
source .venv-orchestrate/bin/activate
cd orchestrate && bash bootstrap_env.sh --reuse-env
```

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

`--min-scale 1` keeps one instance always warm — no cold-start delays when the
triage agent calls the tools mid-conversation.
