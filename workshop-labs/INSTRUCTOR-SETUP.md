# Instructor Setup Guide — Preparing `env.lab` for Participants

This guide walks you through filling in every value in `env.example`, saving it as `env.lab`, and distributing it to participants before the workshop. Complete these steps from the Confluent Cloud UI **before** the lab starts.

> **Why `env.lab` and not `.env`?**
> `.env` is gitignored and cannot be read by IBM Bob. Naming the file `env.lab` allows Bob to read the values during the lab so participants can reference them directly in prompts.

---

## Shared vs. Per-Participant Values

Most credentials in `env.lab` are **shared** — all participants use the same Confluent environment, Schema Registry, global API key, and Flink REST endpoint. You fill these in once and distribute the same file to everyone.

However, the following values are **unique per participant** and must be provided individually to each person:

| Variable | What it is |
|---|---|
| `KAFKA_API_KEY` / `KAFKA_API_SECRET` | Each participant's cluster-scoped API key for their Kafka cluster |
| `KAFKA_CLUSTER_ID` | The ID of each participant's assigned Kafka cluster (`lkc-XXXXX`) |
| `FLINK_COMPUTE_POOL_ID` | Each participant's assigned Flink compute pool (`lfcp-XXXXX`) |
| `FLINK_DATABASE_NAME` | The name of each participant's Kafka cluster (used as Flink default database) |
| `WO_INSTANCE` | Each participant's watsonx Orchestrate instance URL |
| `WO_API_KEY` | Each participant's IBM Cloud API key for watsonx Orchestrate |

Create one `env.lab` file per participant with their individual values filled in, or distribute a shared base file and ask each participant to fill in only their personal values during Step 1.3 of the lab.

---

## Prerequisites

- Admin access to the shared Confluent Cloud environment
- Admin access to a watsonx Orchestrate instance
- The main workshop cluster, Flink compute pool, and Schema Registry already provisioned
- Individual Kafka clusters and Flink compute pools pre-created for each participant (or participants will create their own)

---

## Step 1 — Copy the Template

```bash
cd SWA-Hackathon-2026-assets/workshop-labs
cp env.example env.lab
```

Open `env.lab` in your editor and fill in each section below.

---

## Section 1 — Confluent Cloud Core

### `CONFLUENT_ENVIRONMENT_ID` / `KAFKA_ENV_ID` / `FLINK_ENV_ID`

All three should be the same value — your Confluent Cloud **environment ID**.

**Where to find it:**
1. Sign in to [confluent.cloud](https://confluent.cloud)
2. Click **Environments** in the left nav
3. Click your environment (e.g. `IBM-Hackathon-demo-test`)
4. The ID (`env-XXXXXX`) appears in the **Details** panel on the right

---

### `BOOTSTRAP_SERVERS` / `KAFKA_REST_ENDPOINT` / `KAFKA_CLUSTER_ID`

These identify the **Kafka cluster** participants will use.

**Where to find them:**
1. Inside your environment, click your cluster (e.g. `cluster-gcc`)
2. Click **Cluster overview** in the left sidebar
3. Under **Cluster settings**:
   - **Bootstrap server** → `BOOTSTRAP_SERVERS` (format: `pkc-xxxxx.region.aws.confluent.cloud:9092`)
   - **REST endpoint** → `KAFKA_REST_ENDPOINT` (format: `https://pkc-xxxxx.region.aws.confluent.cloud:443`)
   - **Cluster ID** → `KAFKA_CLUSTER_ID` (format: `lkc-XXXXX`)

---

### `KAFKA_API_KEY` / `KAFKA_API_SECRET`

A **cluster-scoped** API key used by the simulator and dashboard for SASL broker authentication.

> ⚠️ This must be **cluster-scoped**, not a global key. Create it from inside the cluster.

**Where to create it:**
1. Inside your cluster, click **API keys** in the left sidebar
2. Click **+ Add key** → **My account** (or **Service account** for shared labs)
3. Scope: **This cluster** → click **Next** → **Create API key**
4. Copy the key and secret immediately — the secret is shown only once

---

### `CONFLUENT_CLOUD_API_KEY` / `CONFLUENT_CLOUD_API_SECRET`

A **global** API key used by the Confluent MCP server and Flink REST API. One key can be shared across all participants for read operations.

> 💡 `FLINK_API_KEY` and `FLINK_API_SECRET` use the same global key — copy the same values into both sets of variables.

**Where to create it:**
1. Click your **user avatar** (top-right) → **Cloud API keys**
2. Click **+ Add key** → **Global access** → **Next** → **Create API key**
3. Copy key and secret

---

## Section 2 — Schema Registry

### `SCHEMA_REGISTRY_URL` / `SCHEMA_REGISTRY_API_KEY` / `SCHEMA_REGISTRY_API_SECRET`

Schema Registry is provisioned automatically with your environment under the **Essentials** Stream Governance package.

**Where to find the URL:**
1. In your environment left sidebar, click **Schema Registry**
2. Click **Endpoints** → copy the **Public endpoint**
   (format: `https://psrc-XXXXX.region.aws.confluent.cloud`)

**Where to create the API key:**
1. Still in Schema Registry, click **API keys** → **+ Add key**
2. Scope: **My account** → **Create**
3. Copy key and secret

---

## Section 3 — Confluent Flink

### `FLINK_COMPUTE_POOL_ID`

The ID of the Flink compute pool participants will use to run streaming jobs.

**Where to find it:**
1. In your environment, click **Flink** → **Compute pools**
2. Click your pool (e.g. `gcc-pool`)
3. The pool ID (`lfcp-XXXXX`) appears in the URL and in the pool details panel

### `FLINK_REST_ENDPOINT`

The regional Flink REST API base URL. This is determined by the region your cluster is in.

| AWS Region | `FLINK_REST_ENDPOINT` |
|---|---|
| us-east-1 | `https://flink.us-east-1.aws.confluent.cloud` |
| us-east-2 | `https://flink.us-east-2.aws.confluent.cloud` |
| eu-west-1 | `https://flink.eu-west-1.aws.confluent.cloud` |

### `FLINK_ORG_ID`

Your Confluent Cloud **organization UUID**.

**Where to find it:**
1. Click your **user avatar** (top-right) → **Organization settings**
2. Copy the **Organization ID** (a UUID in the format `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)

### `FLINK_CATALOG_NAME`

The name of your Confluent Cloud **environment** (not the environment ID — the human-readable name).  
Example: `IBM-Hackathon-demo-test`

### `FLINK_DATABASE_NAME`

The name of the **Kafka cluster** within that environment that participants will use as their default Flink database.  
Example: `cluster-gcc`

---

## Section 4 — Confluent TableFlow (Iceberg)

TableFlow is optional. Leave all `TABLEFLOW_*` values blank if you are not using historical Iceberg queries in the lab. The lab degrades gracefully without it.

If you are using TableFlow:

### `TABLEFLOW_CATALOG_URI`

**Where to find it:**
1. In your environment, click **TableFlow**
2. Click your TableFlow connector for `flight-events`
3. Copy the **Catalog URI** from the connector details

### `TABLEFLOW_WAREHOUSE`

The S3 (or GCS) path where Iceberg data is written.

**Where to find it:**  
Same TableFlow connector details page → **Warehouse location**

### `TABLEFLOW_NAMESPACE`

The Kafka cluster ID that acts as the Iceberg namespace (format: `lkc-XXXXXXX`).  
This is the same value as `KAFKA_CLUSTER_ID`.

### `TABLEFLOW_API_KEY` / `TABLEFLOW_API_SECRET`

Use the same **global** API key as `CONFLUENT_CLOUD_API_KEY` / `CONFLUENT_CLOUD_API_SECRET`.

---

## Section 5 — watsonx Orchestrate

### `WO_INSTANCE`

The URL of your watsonx Orchestrate instance.  
Example: `https://api.us-south.assistant.watson.cloud.ibm.com/instances/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

**Where to find it:**
1. Sign in to [IBM Cloud](https://cloud.ibm.com)
2. Navigate to your watsonx Orchestrate instance
3. Click **Manage** → copy the **Instance URL**

### `WO_API_KEY`

An IBM Cloud API key with access to the watsonx Orchestrate instance.

**Where to create it:**
1. In [IBM Cloud](https://cloud.ibm.com), click your **avatar** (top-right) → **IBM Cloud API keys**
2. Click **Create an IBM Cloud API key** → name it → **Create**
3. Copy the key immediately — it is shown only once

### `WO_TRIAGE_AGENT_ID`

Leave blank — this is added after the agent is deployed in Lab 2.

---

## Step 2 — Final `env.lab` Checklist

Before distributing, verify every `REPLACE_WITH_*` placeholder has been replaced:

```bash
grep "REPLACE_WITH" env.lab
# Should return no output
```

Also verify no blank required fields remain:

| Variable | Required | Notes |
|---|---|---|
| `BOOTSTRAP_SERVERS` | ✅ | |
| `CONFLUENT_ENVIRONMENT_ID` | ✅ | |
| `KAFKA_API_KEY` / `KAFKA_API_SECRET` | ✅ | Cluster-scoped |
| `KAFKA_REST_ENDPOINT` | ✅ | |
| `KAFKA_CLUSTER_ID` | ✅ | |
| `SCHEMA_REGISTRY_URL` | ✅ | |
| `SCHEMA_REGISTRY_API_KEY` / `SCHEMA_REGISTRY_API_SECRET` | ✅ | |
| `CONFLUENT_CLOUD_API_KEY` / `CONFLUENT_CLOUD_API_SECRET` | ✅ | Global scope |
| `FLINK_COMPUTE_POOL_ID` | ✅ | |
| `FLINK_REST_ENDPOINT` | ✅ | |
| `FLINK_ORG_ID` | ✅ | |
| `FLINK_CATALOG_NAME` | ✅ | Environment name |
| `FLINK_DATABASE_NAME` | ✅ | Cluster name |
| `TABLEFLOW_*` | ⬜ Optional | Leave blank to skip TableFlow |
| `WO_INSTANCE` | ✅ | |
| `WO_API_KEY` | ✅ | |

---

## Step 3 — Distribute to Participants

Distribute `env.lab` to participants as part of the lab starter kit. Participants will:

1. Place `env.lab` in the `workshop-labs/` directory alongside `mcp.json`
2. Open it to read their cluster and API key values when prompted during the lab
3. Reference it in the Confluent MCP server launch command:
   ```bash
   npx @confluentinc/mcp-confluent \
     -c ~/confluent-mcp/config.yaml \
     -e ./env.lab
   ```

> ⚠️ Do **not** commit `env.lab` to git — add it to `.gitignore`. It contains real API keys and secrets.
