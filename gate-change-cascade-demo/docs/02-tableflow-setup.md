# Doc 02 — Confluent TableFlow + Iceberg Setup

**Gate Change Cascade Demo — Step 2**

TableFlow continuously syncs a Kafka topic into an Apache Iceberg table in object storage.
This gives the `flight_triage_agent` a 30-day historical baseline of detected anomalies to
compare against — without any ETL code. This step is **required**: the triage agent uses the
historical baseline to compute the current-vs-historical ratio and select the correct runbook action.

> ⚠️ **Enable TableFlow on `ops-alerts` only.** Do not enable it on `flight-events` or other
> input topics — those tables contain computed columns (`event_time AS $rowtime`) that
> TableFlow cannot process, which will cause a **"schema contains a computed column"** suspension error.

---

## What TableFlow does in this demo

```
ops-alerts (Kafka)   ← Flink writes anomaly detections here
    │
    └──► TableFlow (managed, no code)
              └──► ops-alerts (Iceberg table in S3/GCS)
                        └──► query_flight_history tool (PyIceberg)
                                  └──► flight_triage_agent (historical context)
```

---

## Step 2.1 — Enable TableFlow on `ops-alerts`

> ⚠️ The Flink anomaly detection job must be running and have written at least a few messages
> to `ops-alerts` before you enable TableFlow. TableFlow needs the topic schema to already be
> registered in Schema Registry.

Verify anomaly alerts are flowing with Bob:
```
Create and read a Flink statement that selects the latest 5 rows from ops-alerts
```
```text
mcp__confluent__create-flink-statement
  { "statement": "SELECT * FROM `ops-alerts` LIMIT 5;",
    "statementName": "verify-ops-alerts-tableflow" }

mcp__confluent__read-flink-statement
  { "statementName": "verify-ops-alerts-tableflow", "timeoutInMilliseconds": 20000 }
```

Then in the Confluent Cloud UI:

1. Navigate to **Topics** → `ops-alerts`
2. Click the **TableFlow** tab → **Enable TableFlow**
3. Under **Output format**, select **Iceberg**
4. Under **Storage**, select **Confluent-managed storage**
   - This provisions S3 storage managed entirely by Confluent — no AWS account or bucket needed
5. Under **Sync mode**, leave the default (**Full sync**)
6. Click **Enable TableFlow**

Wait ~2 minutes. The TableFlow tab should show status **Syncing** and display:
- **Iceberg REST endpoint** — copy this as `TABLEFLOW_CATALOG_URI`
- **Warehouse location** — copy this as `TABLEFLOW_WAREHOUSE` (format: `s3://cc-tableflow-****`)
- **Namespace** — copy this as `TABLEFLOW_NAMESPACE` (format: `lkc-*****`)

---

## Step 2.2 — Record TableFlow credentials in `.env`

All three values are shown on the **TableFlow** tab of the `ops-alerts` topic once syncing starts:

| `.env` Variable | Where to find it in the UI |
|---|---|
| `TABLEFLOW_CATALOG_URI` | **Iceberg REST endpoint** field (e.g. `https://tableflow.us-east-1.aws.confluent.cloud/iceberg/rest`) |
| `TABLEFLOW_WAREHOUSE` | **Warehouse location** field (e.g. `s3://cc-tableflow-prod-****`) |
| `TABLEFLOW_NAMESPACE` | **Namespace** field — same as your Kafka cluster ID (e.g. `lkc-yo2mjmo`) |

```env
TABLEFLOW_CATALOG_URI=https://tableflow.us-east-1.aws.confluent.cloud/iceberg/rest
TABLEFLOW_WAREHOUSE=s3://cc-tableflow-prod-****
TABLEFLOW_NAMESPACE=lkc-****
```

---

## Step 2.3 — Verify syncing

**In the Confluent Cloud UI:**

On the **TableFlow** tab of `ops-alerts`, confirm:
- Status shows **Syncing** (not Suspended or Error)
- **Last synced** timestamp is updating
- **Records synced** count is increasing

**Optional — verify via PyIceberg:**

```bash
set -a && source .env && set +a
source .venv/bin/activate
python - <<'EOF'
from pyiceberg.catalog import load_catalog
import os

uri = os.environ["TABLEFLOW_CATALOG_URI"]

cat = load_catalog("tableflow", **{
    "type":              "rest",
    "uri":               uri,
    "warehouse":         os.environ["TABLEFLOW_WAREHOUSE"],
    "credential":        f"{os.environ['CONFLUENT_API_KEY']}:{os.environ['CONFLUENT_API_SECRET']}",
    "oauth2-server-uri": f"{uri}/v1/oauth/tokens",
    "scope":             "catalog",
})
ns = os.environ["TABLEFLOW_NAMESPACE"]
print("Tables:", cat.list_tables(ns))
tbl = cat.load_table(f"{ns}.ops-alerts")
print("Schema:", tbl.schema())
print("Snapshots:", len(list(tbl.snapshots())))
EOF
```

Expected output: `ops-alerts` listed under tables, schema showing `entity_id`, `stream`, `metric`,
`value`, `anomaly_score`, `is_anomaly`, `hub`, `detected_at`, `event_time`.

---

## Step 2.4 — Dry-run without TableFlow

If you skip TableFlow (no object store available), the demo still works end-to-end:
- `query_flight_history` returns `{"status": "tableflow_not_configured"}`
- `flight_triage_agent` includes "Historical baseline: TableFlow not configured (dry-run mode)" in its summary
- All other agent capabilities (Slack, ServiceNow, RAG runbook) work normally

---

**Next:** [03-flink-anomaly.md](03-flink-anomaly.md)
