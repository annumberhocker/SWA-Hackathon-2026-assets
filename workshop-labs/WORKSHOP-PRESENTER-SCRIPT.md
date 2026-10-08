# ⏱️ Workshop Presenter Script: Streaming AI & Agentic Orchestration

**Total Time Allotted:** 30 Minutes  
**Focus:** High-Impact Architecture Overview + Live WXO No-Code UI Demo + Live Bob & Confluent Demo  
**Audience:** Hackathon Participants, Solution Architects, Developers, and AI Practitioners  

---

## ⏰ Time Breakdown (30 Minutes Total)

| Segment | Topic | Time |
|---|---|---|
| **Part 1** | Welcome, Hackathon Context & End-to-End Architecture | 4 mins (0:00 – 0:04) |
| **Part 2** | **Demo 1:** watsonx Orchestrate UI (No-Code Triage Agent & RAG) | 12 mins (0:04 – 0:16) |
| **Part 3** | **Demo 2:** IBM Bob + Confluent Cloud (MCP, Stream Discovery & Flink AI SQL) | 11 mins (0:16 – 0:27) |
| **Part 4** | Full Loop Integration & Hackathon Next Steps | 3 mins (0:27 – 0:30) |

---

## 🎬 Part 1: Welcome & Architecture Overview (4 mins | 0:00 – 0:04)

### 📌 Slide 1: Welcome & Mission
> **Speaker Cues:** Energetic opening. Establish the three pillars: Event Streams, In-Stream ML, and Agentic AI.

**Speaker:**
> *"Welcome everyone to the **Streaming AI with IBM Bob, Confluent Cloud, and watsonx Orchestrate** workshop!*
>
> *Today, we're demonstrating how modern enterprise AI bridges real-time streaming data with autonomous agent reasoning:*
> 1. ***Real-Time Event Streaming & In-Stream AI*** *with Confluent Cloud & Apache Flink.*
> 2. ***Agentic Reasoning & Knowledge Retrieval (RAG)*** *with IBM watsonx Orchestrate.*
> 3. ***Intelligent Developer Orchestration*** *using IBM Bob and the Model Context Protocol (MCP).*
>
> *Our mission: Detect ground operations anomalies from live flight telemetry in milliseconds, and immediately triage them with an AI agent grounded in airline Standard Operating Procedures (SOPs)."*

---

### 📌 Slide 2: End-to-End Solution Architecture
*(Reference diagram: `images/ibm_bob_confluent_wxo_architecture.png`)*

```
[ Flight Telemetry Simulator ]
              │ (gate_wait, departure_delay, turnaround_time)
              ▼
    [ Confluent Cloud: `flight-events` Kafka Topic ]
              │
              ▼
    [ Flink SQL Engine with AI_DETECT_ANOMALIES ]
              │ (2s Tumbling Windows + ML ARIMA baseline)
              ▼
    [ Confluent Cloud: `ops-alerts` Kafka Topic ]
              │
              ▼
    [ watsonx Orchestrate: Flight Triage Agent ]
         ▲               ▲
         │ (RAG)         │ (Automated Triage)
[ Flight Ops Runbook PDF ]  [ Structured Action & ServiceNow Urgency ]
```

**Speaker:**
> *"Here is how data flows from telemetry to resolution:*
>
> 1. ***Telemetry Ingestion:*** *Aircraft telemetry (`gate_wait`, `departure_delay`, `turnaround_time`) streams continuously into Confluent Cloud.*
> 2. ***In-Stream Machine Learning:*** *Apache Flink aggregates events over 2-second tumbling windows and runs Confluent's `AI_DETECT_ANOMALIES` function against historical baselines, publishing high-confidence alerts to `ops-alerts`.*
> 3. ***Agentic Triage:*** *A **Flight Triage Agent** in **watsonx Orchestrate** consumes these alerts, evaluates severity, cross-references a vector knowledge base containing `flight_ops_runbook.pdf`, and generates an actionable mitigation plan with ServiceNow urgency.*
>
> *We will demonstrate this in two parts: first, building the triage agent in the watsonx Orchestrate UI, and second, managing the Confluent streaming pipeline through natural language in IBM Bob!"*

---

## 🖥️ Part 2: Demo 1 — watsonx Orchestrate No-Code Lab (12 mins | 0:04 – 0:16)

*(Switch screen to browser at `cloud.ibm.com`)*

### 1. Navigating IBM Cloud & Launching WXO (~2 mins)
**[Screen Action]:**
1. Navigate to **IBM Cloud → Resource list → AI / Machine Learning**.
2. Click **watsonx Orchestrate** → click **Launch watsonx Orchestrate**.
3. Open the left menu (☰) and click **Build**.

**Speaker:**
> *"In the watsonx Orchestrate console under **Build**, you have a visual studio for building AI assistants, integrating enterprise skills, and managing RAG knowledge bases.*
>
> *Let's create our flight triage agent from scratch."*

---

### 2. Creating the Native Agent & Guardrail Instructions (~4 mins)
**[Screen Action]:** Click **Create agent** → **Create from scratch**.

- **Agent Name:** `flight_triage_agent_demo` *(or your initials)*
- **Description:** `Triages real-time flight schedule anomaly alerts from Confluent Kafka using the Flight Operations Runbook.`
- **Instructions:** Paste the system prompt from `workshop-labs/WXO-No-Code.md`.

**Speaker Talking Points:**
> *"Notice the guardrails in our agent prompt:*
> - ***Deterministic fleet mapping:*** *Resolves aircraft tails like `N303AX` to flight routes like `AX303 (DFW→MIA)`.*
> - ***Severity thresholds:*** *Scores $\ge 0.9$ are flagged as **CRITICAL** (Urgency 1).*
> - ***Anti-hallucination constraint:*** *The agent is instructed to cite verified procedures directly from §1 Gate Operations, §2 Departure Delays, or §3 Turnaround Disruptions of our PDF runbook."*

---

### 3. Ingesting Runbook PDF into Vector Knowledge Base (RAG) (~3 mins)
**[Screen Action]:**
1. Click the **Knowledge** tab at the top of the agent screen.
2. Click **Add source** → **New knowledge** → **Upload files** → **Next**.
3. Select `workshop-labs/orchestrate/knowledge-bases/flight_ops_runbook.pdf`.
4. Enter Name: `Flight Ops Runbook` → click **Save**.

**Speaker:**
> *"Under the hood, watsonx Orchestrate parses the document, creates semantic vector embeddings, and indexes them in an in-memory vector store. When the status changes to **Ready**, our agent is fully equipped for semantic RAG retrieval."*

---

### 4. Live Testing in Draft Preview (~3 mins)
*(Focus on the Draft Preview panel on the right side of the screen)*

**[Screen Action — Scenario A: CRITICAL Alert]:** Paste the CRITICAL payload:
```text
Alert received:
- entity_id: N303AX
- stream: schedule
- metric: gate_wait
- value: 34.5
- unit: minutes
- anomaly_score: 0.96
- hub: DFW
- detected_at: 2026-09-30T17:00:00Z

Please triage this alert and provide runbook recommendations based on the flight_ops_runbook knowledge base.
```

**Speaker:**
> *"The agent maps `N303AX` to Flight AX303, calculates CRITICAL severity (Urgency 1), cites **§1 Gate Operations**, and prescribes **Option A: Immediate Gate Reassignment** with ramp coordinator dispatch.*
>
> *Now, what happens if an anomaly is minor? Let's test a score of 0.38."*

**[Screen Action — Scenario B: LOW Alert]:** Paste the LOW payload:
```text
Alert received:
- entity_id: N404AX
- stream: schedule
- metric: turnaround_time
- value: 18.2
- unit: minutes
- anomaly_score: 0.38
- hub: DFW
- detected_at: 2026-09-30T17:30:00Z

Please triage this alert.
```

**Speaker:**
> *"The agent recognizes low severity, references **§3 Turnaround Disruptions**, and recommends **Option C: Monitor & Maintain Standard Turn Schedule** without causing false alarms.*
>
> *Now let's switch gears: Where did these anomaly alerts come from? Let's jump into **IBM Bob** and manage the streaming pipeline in **Confluent Cloud**!"*

---

## 🤖 Part 3: Demo 2 — Bob + Confluent Cloud Lab (11 mins | 0:16 – 0:27)

*(Switch screen to IBM Bob IDE workspace `SWA-Hackathon-2026-assets`)*

### 1. Natural Language MCP Server Setup (~2 mins)
**[Screen Action]:** Open the Bob chat panel.

**Speaker:**
> *"IBM Bob uses the **Model Context Protocol (MCP)** to interact directly with Confluent Cloud. Instead of manually editing JSON config files, we just ask Bob in plain English:"*

**[Type in Bob Chat]:**
```text
Add the Confluent MCP server configuration from workshop-labs/mcp-confluent.json to .bob/mcp.json. Resolve the paths for node, npx, and the workshop-labs/env.lab file on my machine.
```

**Speaker:**
> *"Bob inspects our machine, finds `node` and `npx`, locates our `env.lab` credentials, and updates `.bob/mcp.json`. In Settings → MCP Servers, we see a green **Connected** status."*

---

### 2. Exploring Confluent Cloud Streams & Schemas (~2 mins)
**[Screen Action]:** Run discovery prompts in Bob Chat.

**[Type in Bob Chat]:**
```text
List all of the clusters in my Confluent Cloud environment
```

**Speaker:**
> *"Bob calls the Confluent MCP `list-clusters` tool and lists our provisioned Kafka clusters.*
> *Now let's inspect the Schema Registry:"*

**[Type in Bob Chat]:**
```text
List all schemas in my Schema Registry
```

**Speaker:**
> *"Bob calls `list-schemas` and surfaces `flight-events-value`—the schema describing our live telemetry stream."*

---

### 3. Deploying In-Stream Anomaly Detection with Flink SQL (~4 mins)
**[Screen Action]:** Open `flink/anomaly_detection_materialized.sql` in editor.

**Speaker:**
> *"Here in `flink/anomaly_detection_materialized.sql`, a single `CREATE OR ALTER MATERIALIZED TABLE` statement handles everything:*
> - *Binds to the `ops-alerts` destination Kafka topic.*
> - *Groups raw `flight-events` into 2-second tumbling windows.*
> - *Calls Confluent's `AI_DETECT_ANOMALIES` model with a 99% confidence threshold.*
> - *Runs continuously in the cloud as a background streaming job.*
>
> *Let's ask Bob to deploy it for us:"*

**[Type in Bob Chat]:**
```text
Read flink/anomaly_detection_materialized.sql and run it as a Flink statement named 'gate-change-anomaly-detection-demo'.
```

**Speaker:**
> *"Bob calls `create-flink-statement`, submits the DDL, and reports back that our materialized table and streaming job are active."*

---

### 4. Querying & Sampling Live Anomaly Alerts in Bob (~3 mins)
**[Screen Action]:** Prompt Bob to query the output stream.

**[Type in Bob Chat]:**
```text
Run a Flink SQL query named 'sample-ops-alerts-demo' to sample 10 messages from the ops-alerts topic:

SELECT * FROM `IBM-Hackathon-demo-test`.`your-cluster-name`.`ops-alerts` /*+ OPTIONS('scan.startup.mode'='earliest-offset') */ LIMIT 10;
```

**Speaker:**
> *"Bob submits the query, fetches the results, and displays live anomaly events where `is_anomaly = true` and `anomaly_score > 0.95`.*
>
> *These are the exact high-confidence alerts that feed into our watsonx Orchestrate triage agent!"*

---

## 🏁 Part 4: Integration & Workshop Roadmap (3 mins | 0:27 – 0:30)

### 📌 Slide: Bringing It All Together
**Speaker:**
> *"Let's summarize the complete picture:*
>
> 1. ***Live Telemetry*** *is ingested into Confluent Cloud.*
> 2. ***Flink AI SQL*** *detects anomalous flight behavior in real-time tumbling windows.*
> 3. ***IBM Bob*** *orchestrates cluster discovery and statement deployments via MCP.*
> 4. ***watsonx Orchestrate*** *triages those alerts via RAG and maps them directly to actionable airline SOPs.*
>
> *Now it's your turn! In your `workshop-labs` directory, you have everything ready:*
> - **Lab 1 (`Bob-and-Confluent.md`):** Hands-on with Bob and Confluent Cloud Flink ML.
> - **Lab 2 (`Bob-and-WXO.md`):** Programmatic agent configuration via the WXO ADK MCP server.
> - **Lab 2 No-Code (`WXO-No-Code.md`):** The browser UI agent builder we demonstrated.
> - **Lab 3 No-Code (`WXO-Extraction-Flow.md`):** Work order document extraction & generative summarization workflows.
>
> *Grab your `env.lab` file, open Bob, and let's get building. Thank you!"*
