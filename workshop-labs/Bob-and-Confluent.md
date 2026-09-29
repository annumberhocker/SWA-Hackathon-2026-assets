# Lab: Bob + Confluent — Real-Time Flight Anomaly Detection

**Hackathon Track: Streaming AI with IBM Bob & Confluent Cloud**

In this lab you will configure the Confluent MCP server inside Bob, create a Kafka topic for
anomaly alerts, and deploy two Flink SQL statements that detect real-time anomalies in a live
flight-events stream. By the end Bob will be orchestrating your entire Confluent Cloud environment
through natural-language prompts.

**What is already running for you:**
- The `flight-events` Kafka topic exists and is populated with watermarked flight metrics
- The flight simulator is producing continuous events (gate_wait, departure_delay, turnaround_time)
- The Confluent environment, cluster, Schema Registry, and Flink compute pool are provisioned

**What you will do in this lab:**
1. Configure the Confluent MCP server in Bob (filling in your own API credentials)
2. Verify the connection and explore the live `flight-events` stream from Bob
3. Create the `ops-alerts` topic using a Bob prompt
4. Deploy the Flink SQL alerts table definition
5. Deploy the Flink SQL anomaly detection job and watch it run

---

## Part 1 — Configure the Confluent MCP Server in Bob

### Step 1.1 — Install Prerequisites

Open a terminal and run:

```bash
# Install nvm (if not already installed)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.zshrc     # or ~/.bashrc on Linux

# Install and activate Node.js 22
nvm install 22
nvm use 22
node --version      # must show v22.x.x

# macOS only — install required native libraries
brew install openssl zstd
```

### Step 1.2 — Install the Confluent MCP Package

```bash
PATH="/opt/homebrew/bin:$PATH" npm install -g @confluentinc/mcp-confluent
```

After installation, note the two paths you will need in the next step:

```bash
# 1. Path to node binary
which node
# example: /Users/you/.nvm/versions/node/v22.14.0/bin/node

# 2. Path to the MCP server entry point
ls $(npm root -g)/@confluentinc/mcp-confluent/dist/index.js
# example: /Users/you/.nvm/versions/node/v22.14.0/lib/node_modules/@confluentinc/mcp-confluent/dist/index.js
```

Copy both paths — you will paste them into the config file in the next step.

### Step 1.3 — Edit `mcp.json` with Your Credentials

Your instructor has given you a pre-filled `mcp.json` template. Open it now:

```bash
open ~/.bob/settings/mcp.json
# or: code ~/.bob/settings/mcp.json
# or: nano ~/.bob/settings/mcp.json
```

The file already contains the correct values for `BOOTSTRAP_SERVERS`, `SCHEMA_REGISTRY_URL`,
`SCHEMA_REGISTRY_API_KEY`, `SCHEMA_REGISTRY_API_SECRET`, `CONFLUENT_CLOUD_API_KEY`,
`CONFLUENT_CLOUD_API_SECRET`, all Flink settings, and the catalog/database names.

**You only need to replace two values** — your personal cluster-scoped Kafka API key and secret,
which were handed out by the instructor:

```json
{
  "mcpServers": {
    "confluent": {
      "command": "/Users/you/.nvm/versions/node/v22.14.0/bin/node",
      "args": [
        "/Users/you/.nvm/versions/node/v22.14.0/lib/node_modules/@confluentinc/mcp-confluent/dist/index.js"
      ],
      "env": {
        "BOOTSTRAP_SERVERS": "pkc-xxxxx.us-east-2.aws.confluent.cloud:9092",
        "KAFKA_API_KEY": "REPLACE_WITH_YOUR_KEY",
        "KAFKA_API_SECRET": "REPLACE_WITH_YOUR_SECRET",
        "SCHEMA_REGISTRY_URL": "https://psrc-xxxxx.us-east-2.aws.confluent.cloud",
        "SCHEMA_REGISTRY_API_KEY": "...",
        "SCHEMA_REGISTRY_API_SECRET": "...",
        "CONFLUENT_CLOUD_API_KEY": "...",
        "CONFLUENT_CLOUD_API_SECRET": "...",
        "FLINK_API_KEY": "...",
        "FLINK_API_SECRET": "...",
        "FLINK_ENV_ID": "env-xxxxxx",
        "FLINK_ORG_ID": "...",
        "FLINK_COMPUTE_POOL_ID": "lfcp-xxxxx",
        "FLINK_REST_ENDPOINT": "https://flink.us-east-2.aws.confluent.cloud",
        "FLINK_CATALOG_NAME": "IBM-Hackathon-demo-test",
        "FLINK_DATABASE_NAME": "REPLACE_WITH_YOUR_CLUSTER_NAME"
      }
    }
  }
}
```

Make these edits:
1. Replace `REPLACE_WITH_YOUR_KEY` with the `KAFKA_API_KEY` from your instructor handout
2. Replace `REPLACE_WITH_YOUR_SECRET` with the `KAFKA_API_SECRET` from your instructor handout
3. Replace `REPLACE_WITH_YOUR_CLUSTER_NAME` with the `CLUSTER_NAME` from your instructor handout
4. Update the `command` and first `args` entry with the two paths you copied in Step 1.2

Save the file.

> ⚠️ **`KAFKA_API_KEY` must be cluster-scoped.** This is a different key type from the global
> Cloud API key already filled in the template. Your instructor has created cluster-scoped keys
> — one per participant — and printed them on the handout sheet.

### Step 1.4 — Verify the Connection in Bob

1. Open Bob
2. Click the **gear icon** (top-right) → **MCP Servers**
3. Find `confluent` in the list — it should show a green **Connected** status

If you see a red error instead:
- Double-check that you replaced both `REPLACE_WITH_YOUR_KEY` and `REPLACE_WITH_YOUR_SECRET`
- Confirm the `command` path points to an actual Node 22 binary (`node --version` in terminal)
- Run the binary directly to see the raw error:
  ```bash
  node <path-to-index.js>
  ```
  Common causes: wrong node path, `openssl`/`zstd` not installed, or a stray space in a secret value.

---

## Part 2 — Explore the Live Stream from Bob

The flight simulator is already running and producing events. Before creating anything, use Bob
to verify data is flowing.

### Step 2.1 — List Topics

In the Bob chat, type:

```
List all topics in my Confluent cluster
```

Bob will call `mcp__confluent__list-topics` and return a list. You should see `flight-events`
in the results.

### Step 2.2 — Check the Schema Registry

Tell Bob your Schema Registry URL once so it reuses it for the rest of the session:

```
My Schema Registry URL is https://psrc-xxxxx.us-east-2.aws.confluent.cloud — use it for all Schema Registry calls
```

> Replace `psrc-xxxxx…` with the `SCHEMA_REGISTRY_URL` value from your `mcp.json`.

Then ask:

```
List all schemas in my Schema Registry
```

Bob calls `mcp__confluent__list-schemas`. You should see `flight-events-value` — the JSON schema
the simulator registered automatically when it started producing.

---

## Part 3 — Create the `ops-alerts` Topic

Flink will write detected anomalies into a topic called `ops-alerts`. Create it now using Bob.

### Step 3.1 — Create the Topic

In the Bob chat, type:

```
Create a Kafka topic called 'ops-alerts'
```

Bob calls:
```
mcp__confluent__create-topics
  { "topicNames": ["ops-alerts"] }
```

### Step 3.2 — Confirm the Topic Exists

```
List all topics in my Confluent cluster
```

You should now see both `flight-events` and `ops-alerts`.

---

## Part 4 — Deploy the Flink Alerts Table

Before the anomaly detection job can write to `ops-alerts`, you need to create a Flink table
definition that binds that topic to a typed schema. This is defined in `flink/alerts_table.sql`.

### Step 4.1 — Understand What the SQL Does

The statement creates a Flink table called `ops-alerts` with the following schema:

| Column | Type | Description |
|---|---|---|
| `entity_id` | STRING | Aircraft identifier |
| `stream` | STRING | Always `"schedule"` in this demo |
| `metric` | STRING | `gate_wait`, `departure_delay`, or `turnaround_time` |
| `value` | DOUBLE | Measured metric value |
| `unit` | STRING | Unit of measure |
| `anomaly_score` | DOUBLE | Score in `[0, 1]` — higher = more anomalous |
| `is_anomaly` | BOOLEAN | `TRUE` when the anomaly detection model fires |
| `hub` | STRING | Airport hub code |
| `detected_at` | TIMESTAMP(3) | Wall-clock time Bob's Flink job emitted the row |
| `event_time` | TIMESTAMP(3) | Event time from the originating window |

The `WATERMARK FOR event_time` clause tells Flink how to handle late-arriving events.
The `WITH ('kafka.cleanup-policy' = 'delete')` clause binds to the **existing** `ops-alerts` topic
you just created — it does not recreate it.

### Step 4.2 — Run the Statement from Bob

Copy the SQL below and paste it into Bob with this prompt:

```
Run Flink SQL statement named 'ops-alerts-table-def' from flink/alerts_table.sql
```

Bob calls:
```
mcp__confluent__create-flink-statement
  {
    "statementName": "ops-alerts-table-def",
    "statement": "CREATE TABLE IF NOT EXISTS `ops-alerts` ..."
  }
```

### Step 4.3 — Verify the Statement Completed

```
Show me the status of the Flink statement named 'ops-alerts-table-def'
```

Bob calls `mcp__confluent__read-flink-statement`. A DDL `CREATE TABLE` statement should reach
**COMPLETED** status quickly (within a few seconds). If it shows **FAILED**, read the error
message Bob returns — a common cause is the `ops-alerts` topic not yet existing (check Part 3).

---

## Part 5 — Deploy the Anomaly Detection Job

This is the main streaming job. It reads from `flight-events`, applies a 10-second tumbling
window to average each metric per aircraft, runs Confluent's `AI_DETECT_ANOMALIES` function over
the windowed averages, and writes rows where `is_anomaly = TRUE` and `anomaly_score > 0.95`
into `ops-alerts`.

### Step 5.1 — Understand the Query

The job is structured in two CTEs:

**`windowed_schedule`** — groups raw events into 10-second tumbling windows and averages each
metric. This reduces noise before anomaly scoring.

**`anomaly_results`** — calls `AI_DETECT_ANOMALIES` as an analytic function over an unbounded
window partitioned by `(entity_id, stream, metric)`. This gives the model full history for each
aircraft-metric pair to build its baseline.

The outer `SELECT` and `WHERE` clause filters to only the rows that are true anomalies with a
high confidence score, then writes them to `ops-alerts`.

Key parameters:
- `minContextSize = 20` — the model waits for 20 windows (~3.5 minutes at 10-second intervals)
  before producing any output. **This is expected behaviour — the first few minutes will appear quiet.**
- `confidencePercentage = 99.0` — requires 99% confidence before flagging an anomaly
- `anomaly_score > 0.95` — additional threshold on the normalized deviation

### Step 5.2 — Run the Statement from Bob

In the Bob chat, type:

```
Read flink/03_anomaly_detection_ai.sql and run it as a long-running Flink streaming job named 'gate-change-anomaly-detection'. It should stay in RUNNING status continuously.
```

Bob calls:
```
mcp__confluent__create-flink-statement
  {
    "statementName": "gate-change-anomaly-detection",
    "statement": "INSERT INTO `ops-alerts` WITH windowed_schedule AS ..."
  }
```

### Step 5.3 — Confirm the Job is Running

```
Show me the status of the Flink statement named 'gate-change-anomaly-detection'
```

You should see status **RUNNING**. Unlike the DDL in Step 4, this INSERT job runs indefinitely —
that is correct and expected. Do not stop it.

### Step 5.4 — List All Running Flink Statements

```
List all my Flink statements
```

Bob calls `mcp__confluent__list-flink-statements`. You should see both:
- `ops-alerts-table-def` — COMPLETED
- `gate-change-anomaly-detection` — RUNNING

### Step 5.5 — Wait for Anomalies (Warmup Period)

The `minContextSize = 20` parameter means the model needs 20 completed 10-second windows
(~3.5 minutes) before it begins scoring. During this warmup period `ops-alerts` will be empty
— this is normal.

After the warmup, ask Bob to check for output:

```
List all Flink statements and tell me which ones are currently running
```

To verify anomalies are flowing into `ops-alerts`, check the topic in the Confluent Cloud UI:
**Topics → ops-alerts → Messages** — you should start seeing rows appear after the warmup.

---

## Part 6 — Explore and Discuss

Once anomalies are flowing, try these Bob prompts to explore the data:

```
Run a Flink SQL query named 'sample-ops-alerts' to show the 10 most recent messages from the ops-alerts topic:

SELECT * FROM `ops-alerts` ORDER BY detected_at DESC LIMIT 10;
```

Bob will call `mcp__confluent__create-flink-statement` to submit the query and then
`mcp__confluent__read-flink-statement` to fetch and display the results. You should see rows
with `is_anomaly = true` and an `anomaly_score` close to or above `0.95`.

```
Search for topics related to 'alerts' in my Schema Registry
```

```
List all Flink statements and show their current status
```

```
Search for topics by name 'ops-alerts'
```

**Discussion questions:**
- What would you need to change to catch anomalies faster? (Hint: look at `minContextSize` and the window interval)
- The `confidencePercentage` is set to 99.0. What happens to alert volume if you lower it to 95.0?
- What downstream system would you connect `ops-alerts` to next in a real airline ops scenario?

---

## Troubleshooting Reference

| Symptom | Likely Cause | Fix |
|---|---|---|
| Bob MCP shows red / Failed | Wrong node path or empty credential in `mcp.json` | Re-check `command`, `KAFKA_API_KEY`, `KAFKA_API_SECRET` |
| `CREATE TABLE` fails with schema conflict | `DISTRIBUTED INTO` was included | Remove `DISTRIBUTED INTO` clause |
| `CREATE TABLE` fails — topic not found | `ops-alerts` topic not created | Redo Part 3 |
| INSERT job shows FAILED immediately | Table definition not run first | Verify `ops-alerts-table-def` is COMPLETED before running the INSERT |
| `ops-alerts` receives no messages after 5 min | Warmup not complete, or threshold too high | Wait the full ~3.5 min warmup; check the simulator is still producing |
| `list-schemas` returns empty | SR URL not set in session | Tell Bob your SR URL (see Step 2.2) |

---

**Lab complete.** The anomaly detection pipeline is live. In the next lab you will connect
the `ops-alerts` consumer to a watsonx Orchestrate supervisor agent that automatically
triages each alert and dispatches notifications.
