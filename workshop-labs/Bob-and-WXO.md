# Lab: Bob + watsonx Orchestrate — Flight Triage Agent & Knowledge Base Setup

**Hackathon Track: Agentic AI with IBM Bob & watsonx Orchestrate (WXO)**

In this lab, you will configure the watsonx Orchestrate ADK MCP server in Bob, import a Flight Operations Runbook as a vector knowledge base from a PDF document, and deploy a native `flight_triage_agent`. By the end of this lab, Bob will be orchestrating watsonx Orchestrate via natural language prompts to perform automated triage of real-time flight anomalies using knowledge base retrieval.

**What is already prepared for you:**
- The Flight Operations Runbook specification: `orchestrate/knowledge-bases/flight_ops_runbook.yaml`
- The Runbook PDF document: `orchestrate/knowledge-bases/flight_ops_runbook.pdf`
- The Flight Triage Agent specification: `orchestrate/agents/flight_triage_agent.yaml`
- The watsonx Orchestrate instance and tenant provisioned with API credentials

**What you will do in this lab:**
1. Configure the `watsonx-orchestrate-adk` MCP server in Bob (filling in your credentials)
2. Verify the connection and explore existing agents, tools, and models
3. Import the Flight Operations Runbook Knowledge Base (`flight_ops_runbook.pdf`)
4. Verify the Knowledge Base indexing and readiness status
5. Create and deploy the `flight_triage_agent` backed exclusively by the `flight_ops_runbook` knowledge base
6. Test and interact with the triage agent using Bob

---

## Part 1 — Configure the watsonx Orchestrate MCP Server in Bob

### Step 1.1 — Install Prerequisites

Ensure you have Python 3.11+ and `uv` / `uvx` installed. You can prompt Bob with:
```
Help me check that I have `uvx` and `Python 3.11` or higher installed. If not, install it.
```
Respond to Bob's prompts through the process.

### Step 1.2 — Download and Unzip the Lab Repository

If you haven't already downloaded the workshop repository, follow the instructions in the [First Step: Get the Repository](START_HERE.md#first-step-get-the-repository) section of `START_HERE.md` to download and extract the repository on your machine.

### Step 1.3 — Configure the watsonx Orchestrate MCP Server in Bob

1. **Open the project folder in Bob**
   In Bob, go to **File → Open** → select the `SWA-Hackathon-2026-assets` folder.

   > **Important:** Opening this folder sets it as your active workspace root, allowing Bob to load project-level MCP tools automatically.

2. **Tell Bob to configure the MCP server**
   In the Bob chat panel, simply type:

   ```
   Add the watsonx Orchestrate MCP server configuration from workshop-labs/mcp-wxo.json to .bob/mcp.json. Use the credentials from workshop-labs/env.lab and set the working directory to the workshop-labs/orchestrate folder.
   ```

   Bob will read your `workshop-labs/env.lab` credentials, resolve the working directory path, and update `.bob/mcp.json` automatically while preserving any existing MCP servers.

### Step 1.4 — Verify the Connection in Bob

1. In Bob, click the **gear icon** (top-right) → **MCP Servers** (or **MCP**).
2. Find `watsonx-orchestrate-adk` and `watsonx-orchestrate-adk-docs` in the list — they should show a green **Connected** status.

---

## Part 2 — Explore watsonx Orchestrate from Bob

Before creating resources, verify connectivity to your WXO tenant.

### Step 2.1 — Check ADK Server Version & Available Models

In the Bob chat, type:

```
Check the watsonx Orchestrate MCP server version and list all available models
```

Bob calls the watsonx MCP `check_version` and `list_models` tools. You will see supported foundation models available on your tenant.

### Step 2.2 — List Current Agents and Knowledge Bases

In the Bob chat, type:

```
List all existing agents and knowledge bases in my watsonx Orchestrate tenant
```

Bob calls the watsonx MCP `list_agents` and `list_knowledge_bases` tools and returns the existing resources configured in your tenant.

---

## Part 3 — Import the Flight Operations Runbook Knowledge Base

The `flight_ops_runbook.pdf` contains standard operating procedures (SOPs) for gate conflicts, turnaround delays, and departure delay mitigations. We will load it into WXO as a searchable vector knowledge base.

### Step 3.1 — Inspect the Knowledge Base Specification

Review the YAML file located at `orchestrate/knowledge-bases/flight_ops_runbook.yaml`:

```yaml
spec_version: v1
kind: knowledge_base
name: flight_ops_runbook
description: >
  Gate change, departure delay, and turnaround anomaly procedures for the
  Gate Change Cascade demo. Reference: GCC-2024 Rev 1.0.
documents:
  - flight_ops_runbook.pdf
```

The document `flight_ops_runbook.pdf` is located in the same directory.

### Step 3.2 — Import the Knowledge Base via Bob

In the Bob chat, type:

```
Import the knowledge base from orchestrate/knowledge-bases/flight_ops_runbook.yaml
```

Bob calls the watsonx MCP `import_knowledge_bases` tool to upload and begin indexing the runbook document.

### Step 3.3 — Check Knowledge Base Indexing Status

Knowledge bases take a few moments to process, chunk, and index the uploaded PDF. Ask Bob to verify:

```
Check the status of the knowledge base named 'flight_ops_runbook'
```

Bob calls the watsonx MCP `check_knowledge_base_status` tool with `name: "flight_ops_runbook"`. Wait until the status returns as **indexed** / **ready**.

---

## Part 4 — Create and Deploy Your Unique `flight_triage_agent_<initials>`

> ⚠️ **Important — Multi-Tenant Sharing:**
> All workshop participants share the same watsonx Orchestrate tenant. To avoid overwriting each other's work, **you must append your initials** to your agent's `name` and `display_name` (for example, `flight_triage_agent_js` for John Smith).

### Step 4.1 — Customize Your Agent Specification

Open `orchestrate/agents/flight_triage_agent.yaml` in your editor:

```yaml
spec_version: v1
kind: native
name: flight_triage_agent_<initials>          # e.g., flight_triage_agent_js
display_name: Flight Triage Agent (<INITIALS>) # e.g., Flight Triage Agent (JS)
description: >
  Triages real-time flight schedule anomaly alerts from Confluent Kafka.
  Uses the Flight Operations Runbook knowledge base to produce structured
  recommendations and mitigation options for operational disruptions.

llm: groq/openai/gpt-oss-120b
style: react_core
collaborators: []
tools: []

knowledge_base:
  - flight_ops_runbook
...
```

Edit the file to:
1. Replace `<initials>` in `name` with your initials in lowercase (e.g., `flight_triage_agent_js`).
2. Replace `<INITIALS>` in `display_name` with your initials in uppercase (e.g., `Flight Triage Agent (JS)`).
3. Save the file.

Key properties:
- **`name`**: `flight_triage_agent_<initials>` (unique per participant)
- **`llm`**: `groq/openai/gpt-oss-120b` (or your preferred tenant LLM, e.g. `watsonx/meta-llama/llama-3-3-70b-instruct`)
- **`style`**: `react_core`
- **`tools`**: `[]` (pure knowledge-base agent — relies solely on RAG retrieval from the Runbook PDF)
- **`knowledge_base`**: `['flight_ops_runbook']`
- **`instructions`**: Guides the LLM to extract anomaly metrics, determine severity, retrieve matching SOPs from the `flight_ops_runbook` PDF (§1 Gate Operations, §2 Departure Delays, §3 Turnaround Disruptions), select mitigation options based on severity, and output a structured triage summary.

### Step 4.2 — Import the Agent from Bob

In the Bob chat, ask Bob to import your agent spec file (or instruct Bob to create the agent with your unique name):

```
Import the agent from orchestrate/agents/flight_triage_agent.yaml
```

Bob calls the watsonx MCP `import_agent` tool to register your custom agent definition with watsonx Orchestrate.

### Step 4.3 — Confirm Your Agent is Listed

In the Bob chat, type:

```
List my native agents and confirm that flight_triage_agent_<initials> is available
```

Bob calls the watsonx MCP `list_agents` tool with `kind: "native"`. You should see `flight_triage_agent_<initials>` registered and attached to `flight_ops_runbook`.

---

## Part 5 — Test and Interact with Your Triage Agent

Let's test your triage agent with a simulated anomaly alert to verify that it retrieves information from the loaded `flight_ops_runbook.pdf`.

### Step 5.1 — Chat with the Triage Agent

Send an anomaly alert payload to your agent via Bob (replace `<initials>` with your initials):

In the Bob chat, type:

```
Chat with the agent 'flight_triage_agent_<initials>' with the following alert payload:

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

Bob calls the watsonx MCP `chat_with_agent` tool to pass the anomaly payload to your agent and retrieve its triage analysis.

### Step 5.2 — Inspect the Agent's Response

Verify that the agent's output:
1. Maps `N303AX` to **Flight AX303** (DFW → MIA).
2. Calculates severity as **CRITICAL** (since `anomaly_score = 0.96 >= 0.9`).
3. Determines ServiceNow Urgency as **1**.
4. Cites the **Gate Operations (§1)** section of the `flight_ops_runbook.pdf` knowledge base.
5. Selects **Option A (Immediate Gate Reassignment)** as the primary recommendation.
6. Returns a structured triage summary formatted as specified.

---

## Part 6 — Explore and Discuss

Try asking your agent different queries to test runbook retrieval across various disruption scenarios (replace `<initials>` with your initials):

```
Chat with the agent 'flight_triage_agent_<initials>' for this alert:
- entity_id: N101AX
- stream: schedule
- metric: departure_delay
- value: 22.0
- unit: minutes
- anomaly_score: 0.75
- hub: ORD
- detected_at: 2026-09-30T17:15:00Z
```

```
Ask 'flight_triage_agent_<initials>': "What is the procedure outlined in the runbook for a turnaround time anomaly exceeding 45 minutes at ORD?"
```

```
Ask 'flight_triage_agent_<initials>': "What are the escalation triggers for departure delays under Section 2 of the runbook?"
```

**Discussion questions:**
- How does grounding the triage agent in a PDF runbook eliminate LLM hallucination during incident response?
- What is the benefit of keeping the triage agent pure-knowledge (RAG only) while letting a supervisor agent handle notifications and integrations?
- How can you update or expand the runbook PDF as operational SOPs evolve without modifying the agent prompt or code?

---

## Troubleshooting Reference

| Symptom | Likely Cause | Fix |
|---|---|---|
| Bob MCP shows red / Disconnected | Invalid `WO_API_KEY` or `WO_INSTANCE` in `mcp.json` | Check your credentials and re-open Bob settings |
| Knowledge base import fails | Path to `flight_ops_runbook.pdf` or `.yaml` is incorrect | Ensure paths are relative to `WXO_MCP_WORKING_DIRECTORY` or provide full absolute paths |
| Agent fails to cite runbook content | Knowledge base still indexing | Run `check_knowledge_base_status` until status shows `indexed` |
| LLM model error during chat | Specified LLM not available on tenant | Use `list_models` and update `llm` in the agent configuration |
| MCP tool execution timeout | Network latency or large PDF indexing | Increase `"timeout": 300` in `mcp.json` |

## Additional References

[Tutorial - Build agentic workflows with watsonx Orchestrate and IBM Bob](https://developer.ibm.com/tutorials/build-programmatic-agentic-workflows-watsonx-orchestrate-bob/)

---

**Lab complete.** You have successfully integrated Bob with watsonx Orchestrate, loaded an operational runbook PDF into a vector knowledge base, and deployed an intelligent flight triage agent driven entirely by RAG knowledge base retrieval.
