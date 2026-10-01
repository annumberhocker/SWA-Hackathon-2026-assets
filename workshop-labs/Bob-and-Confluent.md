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
3. Deploy the Flink materialized table that creates the `ops-alerts` topic and starts the anomaly detection job in one step

---

## Part 1 — Configure the Confluent MCP Server in Bob

### Step 1.1 — Install Prerequisites

Open a terminal and run:

```bash
# Install nvm (if not already installed)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.zshrc     # or ~/.bashrc on Linux

# Install and activate Node.js 22 if you have an earlier version
nvm install 22
nvm use 22
node --version      # must show v22.x.x
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

In this lab directory, there is a pre-filled `mcp-confluent.json` template. If you don't already have a `~/.bob/settings/mcp.json` file, copy the provided `mcp-confluent.json` file into `~/.bob/settings/mcp.json`. If you do, just add the `confluent` stanza from the `mcp-confluent.json` file to the list of other mcp servers defined

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

### Step 1.5 - Test MCP server

```
npx @confluentinc/mcp-confluent \
  -c /FULL/PATH/confluent-mcp/config.yaml \
  -e ./.env
```
You can also verify which tools are available with:
```bash
npx @confluentinc/mcp-confluent \
  --config ./config.yaml \
  -e ./.env \
  --list-tools
  ```

### Step 1.6 — Verify the Connection in Bob

1. Open Bob
2. Click the **gear icon** (top-right) → **MCP Servers**
3. Find `confluent` in the list — it should show a green **Connected** status


---

## Part 2 — Explore the Confluent cloud account

### Step 2.1 — Set environment
Tell Bob which Environment you are working in:

```
My confluent cloud env is env-xxxxx
```
> Replace `env-xxxxx` with the `FLINK_ENV_ID` value from your `.env` file.

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

> Replace `psrc-xxxxx…` with the `SCHEMA_REGISTRY_URL` value from your `.env` file.

Then ask:

```
List all schemas in my Schema Registry
```

Bob calls `mcp__confluent__list-schemas`. You should see `flight-events-value` — the JSON schema
the simulator registered automatically when it started producing.

---

## Part 3 — Deploy the Anomaly Detection Pipeline

The flight simulator is continuously producing telemetry events — gate wait times, departure delays, and turnaround durations — into the `flight-events` Kafka topic. In this part you will deploy a Flink streaming job that reads those events in real time, averages each metric over 10-second windows, and runs Confluent's `AI_DETECT_ANOMALIES` function to identify aircraft or flights behaving outside their normal baseline. When an anomaly is confirmed with high confidence, the job writes an alert record to a new `ops-alerts` topic, which the watsonx Orchestrate triage agent in the next lab will consume and act on.

A single `CREATE OR ALTER MATERIALIZED TABLE` statement in `flink/anomaly_detection_materialized.sql` does everything in one shot: it creates the `ops-alerts` Kafka topic, defines the table schema, and starts the continuous anomaly detection job — all without any manual topic creation or separate DDL step.

### Step 3.1 — Understand What the SQL Does

The file `flink/anomaly_detection_materialized.sql` does three things in one statement:

1. **Creates (or evolves) the `ops-alerts` table** — defines all columns, the `WATERMARK`, and binds to the `ops-alerts` Kafka topic with `cleanup-policy = delete`.
2. **Runs the streaming query continuously** — reads from `flight-events`, applies a 10-second tumbling window per aircraft + metric, calls `AI_DETECT_ANOMALIES`, and writes only confirmed anomalies to `ops-alerts`.
3. **Stays RUNNING indefinitely** — `START_MODE = RESUME_OR_FROM_BEGINNING` means Flink resumes from where it left off if the statement is restarted.

The query is structured in two CTEs:

**`windowed_schedule`** — groups raw events into 10-second tumbling windows and averages each metric. This reduces noise before anomaly scoring.

**`anomaly_results`** — calls `AI_DETECT_ANOMALIES` as an analytic function over an unbounded window partitioned by `(entity_id, stream, metric)`. This gives the model full history for each aircraft-metric pair to build its baseline.

The outer `SELECT` and `WHERE` filters to only true anomalies with a high confidence score and writes them to `ops-alerts`.

Key parameters:
- `minContextSize = 20` — the model waits for 20 windows (~3.5 minutes at 10-second intervals) before producing any output. **This is expected behaviour — the first few minutes will appear quiet.**
- `confidencePercentage = 99.0` — requires 99% confidence before flagging an anomaly
- `anomaly_score > 0.95` — additional threshold on the normalized deviation

### Step 3.2 — Run the Statement from Bob

In the Bob chat, type:

```
Read flink/anomaly_detection_materialized.sql and run it as a Flink statement named 'gate-change-anomaly-detection'. It should stay in RUNNING status continuously.
```

Bob calls `mcp__confluent__create-flink-statement` with the full SQL from the file.

### Step 3.3 — Confirm the Job is Running

```
Show me the status of the Flink statement named 'gate-change-anomaly-detection'
```

You should see status **RUNNING**. This job runs indefinitely — that is correct and expected. Do not stop it.

### Step 3.4 — Wait for Anomalies (Warmup Period)

The `minContextSize = 20` parameter means the model needs 20 completed 10-second windows (~3.5 minutes) before it begins scoring. During this warmup period `ops-alerts` will be empty — this is normal.

To verify anomalies are flowing into `ops-alerts` after the warmup, check the topic in the Confluent Cloud UI: **Topics → ops-alerts → Messages** — you should start seeing rows appear.

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
| INSERT job shows FAILED immediately | Materialized table statement failed | Check that `flink/anomaly_detection_materialized.sql` was submitted without modification |
| `ops-alerts` receives no messages after 5 min | Warmup not complete, or threshold too high | Wait the full ~3.5 min warmup; check the simulator is still producing |
| `list-schemas` returns empty | SR URL not set in session | Tell Bob your SR URL (see Step 2.2) |

---

**Lab complete.** The anomaly detection pipeline is live. In the next lab you will
create a watsonx Orchestrate triage agent that will triage alerts using a knowledge base.

## References

[Confluent MCP Server](https://docs.confluent.io/cloud/current/ai/ai-tools/open-source-mcp-server.html#configure-your-mcp-client)
