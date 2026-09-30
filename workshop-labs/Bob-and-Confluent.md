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

### Step 1.2 — Generate the Confluent MCP configuration

```bash
mkdir ~/confluent-mcp
cd ~/confluent-mcp
npx @confluentinc/mcp-confluent --init-config
```
The directory will contain a new `config.yaml` file: 


### Step 1.3 — Update Your Credentials

Your instructor has given you a pre-filled `.env` file. Edit it:

```bash
# From the SWA-Hackathon-2026-assets/workshop-labs directory
open ./.env
# or: code ./.env
# or: nano ./.env
```

Make these edits:
1. Replace `REPLACE_WITH_YOUR_KEY` with the provided `KAFKA_API_KEY`
2. Replace `REPLACE_WITH_YOUR_SECRET` with the provided `KAFKA_API_SECRET`
3. Replace `REPLACE_WITH_YOUR_CLUSTER_ID` with the provided `KAFKA_CLUSTER_ID`
4. Replace `REPLACE_WITH_YOUR_COMPUTE_POOL_ID` with the provided `FLINK_COMPUTE_POOL_ID`
5. Replace `REPLACE_WITH_YOUR_CLUSTER_NAME` with the provided `FLINK_DATABASE_NAME`

Save the file

### Step 1.4 — Update `mcp.json` 

Your instructor has given you a pre-filled `mcp-confluent.json` template. If you don't already have a `~/.bob/settings/mcp.json` file, copy the provided `mcp-confluent.json` file into `~/.bob/settings/mcp.json`. If you do, just add the `confluent` stanza from the `mcp-confluent.json` file to the list of other mcp servers defined

Replace the `/FULL/PATH` values accordingly: 
```
 "confluent": {
   "command": "npx",
   "args": [
     "-y",
     "@confluentinc/mcp-confluent",
     "-c",
     "/FULL/PATH/confluent-mcp/config.yaml",
     "-e",
     "/FULL/PATH/swa-hackathon-2026/assets/workshop-labs/.env"
   ],
   "cwd": "/FULL/PATH/confluent-mcp",
   "disabled": false
 }
```

Save the file.

### Step 1.4 Test MCP server

```
npx @confluentinc/mcp-confluent \
  -c /FULL/PATH/confluent-mcp/config.yaml \
  -e ./.env
```
You can also verify which tools are available with:
```bash
npx @confluentinc/mcp-confluent \
  --config ./config.yaml \
  --list-tools
  ```

### Step 1.5 — Verify the Connection in Bob

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

## Part 2 — Explore the Confluent cloud account

### Step 2.1 — Set environment
Tell Bob which Environment you are working in:

```
My confluent cloud env is env-xxxxx
```
> Replace `env-xxxxx` with the `FLINK_ENV_ID` value from your `mcp.json`.

### Step 2.2 — List clusters

Next, ask Bob to list all of the clusters in the environment: 

```
List all of the clusters in my Confluent Cloud environment
```

Bob will call mcp__confluent__list-clusters and return a list.

### Step 2.3 — List Schema Registry information

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

Tell Bob what cluster you are using:

```
My Confluent cluster is `my-cluster`
```
> Replace `my-cluster` with the cluster name assigned to you provided by your instructor.

Then in Bob chat, type:

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

You should now see `ops-alerts`.

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
Read flink/anomaly_detection.sql and run it as a long-running Flink streaming job named 'gate-change-anomaly-detection'. It should stay in RUNNING status continuously.
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

After the warm-up, ask Bob to check for output:

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

**Lab complete.** The anomaly detection pipeline is live. In the next lab you will
create a watsonx Orchestrate triage agent that will triage alerts using a knowledge base.
