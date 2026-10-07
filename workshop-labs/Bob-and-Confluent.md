# Lab: Bob + Confluent — Real-Time Flight Anomaly Detection

**Hackathon Track: Streaming AI with IBM Bob & Confluent Cloud**

In this lab you will configure the Confluent MCP server inside Bob, and deploy a Flink SQL
statement that detects real-time anomalies in a live flight-events stream. By the end Bob will
be orchestrating your entire Confluent Cloud environment through natural-language prompts.

**What is already running for you:**
- The `flight-events` Kafka topic exists and is populated with watermarked flight metrics
- The flight simulator is producing continuous events (gate_wait, departure_delay, turnaround_time)
- The Confluent environment, Cluster, Schema Registry, and Flink compute pool are provisioned
- The instructor has given you an `env.lab` file with all of your credentials pre-filled

**What you will do in this lab:**
1. Create project-level `mcp.json` so Bob can connect to the Confluent
2. Explore the live `flight-events` stream from Bob
3. Deploy the Flink materialized table that creates the `ops-alerts` topic and starts the anomaly detection job

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
node --version
which node   
which npx    
```

### Step 1.2 — Clone the Lab Repository

If you haven't already, clone the hackathon assets repository to your local machine. From a terminal window type the following commands:

```bash
git clone https://github.com/your-org/SWA-Hackathon-2026-assets.git
cd SWA-Hackathon-2026-assets
```

### Step 1.3 — Save Your `env.lab` File

Your instructor will provide you with a personalised `env` file that contains your specific
cluster details and API keys. Save it into the following directory:

```
SWA-Hackathon-2026-assets/workshop-labs/env.lab
```

You can do this from the terminal after you have downloaded the file:

```bash
# Copy the file your instructor provided to the correct location
cp ~/Downloads/env.<name> ~/path/to/SWA-Hackathon-2026-assets/workshop-labs/env.lab
```

Or drag and drop it into the `workshop-labs/` folder using Finder.


### Step 1.4 — Open the Project in Bob and Register the MCP Server

**1. Open the project folder in Bob**

In Bob, go to **File → Open** → select the `SWA-Hackathon-2026-assets` folder

This sets `SWA-Hackathon-2026-assets/` as the project workspace, which is required for the
project-level MCP configuration to take effect.

**2. Open the Bob MCP settings**

- Click the **gear icon** (top-right) → **MCP**
- Click **+** → set **Configuration Scope** to `SWA-Hackathon-2026-assets`

Bob will create and open a `.bob/mcp.json` file at the project root. 

**3. Paste the MCP server configuration**

Copy the full contents of `workshop-labs/mcp-confluent.json` and paste them into this new `.bob/mcp.json`, replacing the scaffolding:

```json
{
  "mcpServers": {
    "confluent": {
      "command": "/FULL/PATH/.nvm/versions/node/v22.23.3/bin/node",
      "args": [
        "FULL/PATH/.nvm/versions/node/v22.23.3/bin/npx",
        "-y",
        "@confluentinc/mcp-confluent",
        "-e",
        "/FULL/PATH/SWA-Hackathon-2026-assets/workshop-labs/env.lab"
      ],
      "disabled": false
    }
  }
}
```

**4. Replace the path placeholder**

Replace `/FULL/PATH/SWA-Hackathon-2026-assets` with the actual path on your machine. To find it, run:

```bash
echo $(pwd)/workshop-labs/env.lab
# Example output: /Users/yourname/projects/SWA-Hackathon-2026-assets/workshop-labs/env.lab
```

So your final `.bob/mcp.json` entry should look like:

```json
"-e",
"/Users/yourname/projects/SWA-Hackathon-2026-assets/workshop-labs/env.lab"
```

**5. Save the file**

Save `.bob/mcp.json`. Bob will detect the change and automatically start the Confluent MCP server
using the credentials in your `env.lab` file.

### Step 1.5 — Verify the Connection in Bob

1. In Bob, click the **gear icon** (top-right) → **MCP Servers**
2. Find `confluent` in the list — it should show a green **Connected** status

If it shows red, see the [Troubleshooting](#troubleshooting-reference) section at the bottom.

---

## Part 2 — Explore the Confluent Cloud Account

### Step 2.1 — Set Environment

Tell Bob which Confluent environment you are working in:

```
My Confluent Cloud environment ID is env-9o530m
```

### Step 2.2 — List Clusters

Ask Bob to list the clusters in the environment:

```
List all of the clusters in my Confluent Cloud environment
```

Bob calls `mcp__confluent__list-clusters` and returns a list. Confirm you can see your assigned cluster.

### Step 2.3 — List Schema Registry Information

Tell Bob your Schema Registry URL so it reuses it for the rest of the session:

```
My Schema Registry URL is https://psrc-zpjqd6q.us-east-2.aws.confluent.cloud — use it for all Schema Registry calls
```

Then ask:

```
List all schemas in my Schema Registry
```

Bob calls `mcp__confluent__list-schemas`. You should see `flight-events-value` — the JSON schema
the simulator registered when it started producing.

---

## Part 3 — Deploy the Anomaly Detection Pipeline

The flight simulator is continuously producing telemetry events — gate wait times, departure delays,
and turnaround durations — into the `flight-events` Kafka topic. In this part you will deploy a
Flink streaming job that reads those events in real time, averages each metric over 2-second
windows, and runs Confluent's `AI_DETECT_ANOMALIES` function to identify aircraft behaving outside
their normal baseline. When an anomaly is confirmed with high confidence, the job writes an alert
record to a new `ops-alerts` topic, which the watsonx Orchestrate triage agent in the next lab
will consume and act on.

A single `CREATE OR ALTER MATERIALIZED TABLE` statement in `flink/anomaly_detection_materialized.sql`
does everything in one shot: it creates the `ops-alerts` Kafka topic, defines the table schema, and
starts the continuous anomaly detection job — all without any manual topic creation or separate DDL step.

### Step 3.1 — Understand What the SQL Does

The file `flink/anomaly_detection_materialized.sql` does three things in one statement:

1. **Creates (or evolves) the `ops-alerts` table** — defines all columns, the `WATERMARK`, and
   binds to the `ops-alerts` Kafka topic.
2. **Runs the streaming query continuously** — reads from `flight-events`, applies a 2-second
   tumbling window per aircraft + metric, calls `AI_DETECT_ANOMALIES`, and writes only confirmed
   anomalies to `ops-alerts`.
3. **Stays RUNNING indefinitely** — `START_MODE = RESUME_OR_FROM_BEGINNING` means Flink resumes
   from where it left off if the statement is restarted.

The query is structured in two CTEs:

**`windowed_schedule`** — groups raw events into 2-second tumbling windows and averages each
metric. This reduces noise before anomaly scoring.

**`anomaly_results`** — calls `AI_DETECT_ANOMALIES` as an analytic function over an unbounded
window partitioned by `(entity_id, stream, metric)`. This gives the model full history per
aircraft-metric pair to build its baseline.

The outer `SELECT` and `WHERE` filters to only true anomalies with a high confidence score.

Key parameters:
- `minContextSize = 5` — the model waits for 5 completed 2-second windows (~10 seconds)
  before producing any output. **This is expected — the first few seconds will appear quiet.**
- `confidencePercentage = 99.0` — requires 99% confidence before flagging an anomaly
- `anomaly_score > 0.95` — additional threshold on the normalized deviation

### Step 3.2 — Update the Cluster Name in the SQL

Open `flink/anomaly_detection_materialized.sql` and replace the `REPLACE_WITH_YOUR_CLUSTER_NAME`
placeholder with the value of `FLINK_DATABASE_NAME` from your `workshop-labs/env.lab` file:

```sql
-- Before:
CREATE OR ALTER MATERIALIZED TABLE `IBM-Hackathon-demo-test`.`REPLACE_WITH_YOUR_CLUSTER_NAME`.`ops-alerts` (

-- After (example, using FLINK_DATABASE_NAME=your-cluster-name from env.lab):
CREATE OR ALTER MATERIALIZED TABLE `IBM-Hackathon-demo-test`.`your-cluster-name`.`ops-alerts` (
```

Save the file before continuing.

### Step 3.3 — Run the Statement from Bob

In the Bob chat, type (replacing `xx` with your initials):

```
Read flink/anomaly_detection_materialized.sql and run it as a Flink statement named 'gate-change-anomaly-detection-xx'.
```

> **Why add your initials?** All participants share the same Confluent Cloud environment. Appending
> your initials (e.g. `gate-change-anomaly-detection-jk`) makes your statement easy to identify
> in the Confluent UI under **Flink → Statements**.

Bob calls `mcp__confluent__create-flink-statement` with the full SQL from the file.

### Step 3.4 — Confirm the Job is Running

```
Show me the status of the Flink statement named 'gate-change-anomaly-detection-xx'
```

You should see status **COMPLETED**. The `CREATE OR ALTER MATERIALIZED TABLE` DDL completes
immediately once Confluent registers the table and hands off to the background streaming refresh
job. The continuous anomaly detection is now running in the background, writing to
`your-cluster.ops-alerts`. Expect the first anomalies to appear after an ~10 second warmup.

### Step 3.5 — Wait for Anomalies (Warmup Period)

The `minContextSize = 5` parameter means the model needs 5 completed 2-second windows
(~10 seconds) before it begins scoring. During this warmup period `ops-alerts` will be empty —
this is normal.

To verify anomalies are flowing after the warmup, check the topic in the Confluent Cloud UI:
**Topics → ops-alerts → Messages** — you should start seeing rows appear.

---

## Part 4 — Explore and Discuss

Once anomalies are flowing, try these Bob prompts:

```
Run a Flink SQL query named 'sample-ops-alerts-xx' to sample 10 messages from the ops-alerts topic:

SELECT * FROM `IBM-Hackathon-demo-test`.`your-cluster-name`.`ops-alerts` /*+ OPTIONS('scan.startup.mode'='earliest-offset') */ LIMIT 10;
```

> Replace `your-cluster-name` with your cluster name and `xx` with your initials.

The `/*+ OPTIONS('scan.startup.mode'='earliest-offset') */` hint is required — without it Flink
reads from the current offset and returns no results for messages already in the topic.

Bob calls `mcp__confluent__create-flink-statement` to submit the query and then
`mcp__confluent__get-flink-statement-results` to fetch and display the results. You should see
rows with `is_anomaly = true` and an `anomaly_score` close to or above `0.95`.

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
- What would you change to catch anomalies faster? (Hint: look at `minContextSize` and the window interval)
- The `confidencePercentage` is set to 99.0. What happens to alert volume if you lower it to 95.0?
- What downstream system would you connect `ops-alerts` to next in a real airline ops scenario?

---

## Troubleshooting Reference

| Symptom | Likely Cause | Fix |
|---|---|---|
| Bob MCP shows red / Failed | `npx` not on Bob's PATH (nvm or Homebrew install) | Install Node.js from **https://nodejs.org** (LTS `.pkg` installer) — this puts `npx` in `/usr/local/bin` which Bob can always find |
| Bob MCP shows red / Failed | `/FULL/PATH` placeholder not replaced in `.bob/mcp.json` | Replace with the absolute path from `echo $(pwd)/workshop-labs/env.lab` (Step 1.4) |
| Bob MCP shows red / Failed | Wrong or missing credentials in `env.lab` | Re-check that your `workshop-labs/env.lab` file was saved correctly and the path in `.bob/mcp.json` points to it (Step 1.4) |
| Bob MCP shows red / Failed | Bob opened without project root as workspace | Open Bob with `SWA-Hackathon-2026-assets/` as the workspace folder |
| MCP server starts but Flink tools missing | Flink credentials missing from `env.lab` | Ensure all Flink fields are set in `env.lab`: `FLINK_REST_ENDPOINT`, `FLINK_API_KEY`, `FLINK_API_SECRET`, `FLINK_ORG_ID`, `FLINK_ENV_ID`, `FLINK_COMPUTE_POOL_ID` |
| `CREATE TABLE` fails with schema conflict | `DISTRIBUTED INTO` was included | Remove `DISTRIBUTED INTO` clause from the SQL |
| INSERT job shows FAILED immediately | Materialized table statement failed | Verify `flink/anomaly_detection_materialized.sql` cluster name was updated in Step 3.2 |
| `ops-alerts` receives no messages after 5 min | Warmup not complete, or threshold too high | Wait for the warmup to complete; confirm the simulator is still producing |
| `list-schemas` returns empty | SR URL not set in session | Tell Bob your SR URL (Step 2.3) |

---

**Lab complete.** The anomaly detection pipeline is live. In the next lab you will
create a watsonx Orchestrate triage agent that will triage alerts using a knowledge base.

## References

- [Confluent Open-Source MCP Server docs](https://docs.confluent.io/cloud/current/ai/ai-tools/open-source-mcp-server.html)
- [mcp-confluent GitHub repository](https://github.com/confluentinc/mcp-confluent)
- [mcp-confluent Configuration Guide](https://github.com/confluentinc/mcp-confluent/blob/main/CONFIGURATION.md)
