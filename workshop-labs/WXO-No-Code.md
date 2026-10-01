# No-Code Lab: Build the Flight Triage Agent Using the watsonx Orchestrate UI

**Hackathon Track: Agentic AI — No-Code Path**

In this lab, you will build the same `flight_triage_agent` from the main workshop — entirely through the watsonx Orchestrate (WXO) browser UI — without writing any code or running any CLI commands. By the end, you will have a fully deployed triage agent grounded in the Flight Operations Runbook, ready to process real-time anomaly alerts.

> **Note:** This is the no-code alternative to [Lab 2: Bob + watsonx Orchestrate](Bob-and-WXO.md). You only need to complete one of them. Choose this path if you prefer working in a browser UI over using IBM Bob and the ADK MCP server.

---

## What You Will Build

A **native AI agent** in watsonx Orchestrate that:
- Is backed by the **Flight Operations Runbook** PDF as a vector knowledge base
- Triages anomaly alerts produced by the Confluent Kafka `ops-alerts` topic
- Returns structured triage summaries with runbook references and mitigation options

---

## Prerequisites

Before starting, make sure you have:
- Your **WXO tenant URL** (provided by the instructor)
- Your **WXO login credentials** (IBMid or tenant-specific credentials)
- The **`flight_ops_runbook.pdf`** file downloaded from this repository:
  `workshop-labs/orchestrate/knowledge-bases/flight_ops_runbook.pdf`
- Your **initials** ready to append to resource names (all participants share the same tenant)

---

## Part 1 — Log In to watsonx Orchestrate

### Step 1.1 — Open the WXO Console

Navigate to your tenant URL in a browser (provided by the instructor). It will look like:

```
https://<your-tenant-region>.orchestrate.ibm.com
```

> 📸 **Screenshot placeholder:** WXO login page showing the IBMid sign-in form.
> `[SCREENSHOT: wxo-login.png]`

### Step 1.2 — Sign In

Enter your credentials and click **Sign in**. You will land on the watsonx Orchestrate home screen.

> 📸 **Screenshot placeholder:** WXO home/dashboard screen after successful login.
> `[SCREENSHOT: wxo-home-dashboard.png]`

---

## Part 2 — Import the Flight Operations Runbook Knowledge Base

The triage agent relies on RAG (Retrieval-Augmented Generation) over the Flight Operations Runbook PDF. You must create and index the knowledge base before creating the agent.

### Step 2.1 — Navigate to Knowledge Bases

From the left navigation sidebar, click **AI Builders** → **Knowledge Bases**.

> 📸 **Screenshot placeholder:** Left nav sidebar with "AI Builders" expanded and "Knowledge Bases" highlighted.
> `[SCREENSHOT: wxo-nav-knowledge-bases.png]`

### Step 2.2 — Create a New Knowledge Base

Click the **New knowledge base** button (top-right).

> 📸 **Screenshot placeholder:** Knowledge Bases list page with the "New knowledge base" button highlighted.
> `[SCREENSHOT: wxo-kb-list-new-button.png]`

### Step 2.3 — Fill in Knowledge Base Details

In the creation dialog, fill in:

| Field | Value |
|---|---|
| **Name** | `flight_ops_runbook` |
| **Description** | `Gate change, departure delay, and turnaround anomaly procedures for the Gate Change Cascade demo. Reference: GCC-2024 Rev 1.0.` |

> 📸 **Screenshot placeholder:** "New knowledge base" creation form with Name and Description fields filled in.
> `[SCREENSHOT: wxo-kb-create-form.png]`

### Step 2.4 — Upload the Runbook PDF

Click **Add files** (or drag and drop) to upload the runbook:

1. Click **Add files** or the upload area.
2. Navigate to and select `flight_ops_runbook.pdf` from where you downloaded it.
3. Confirm the file appears in the upload list.

> 📸 **Screenshot placeholder:** File upload dialog with `flight_ops_runbook.pdf` selected or shown in the upload area.
> `[SCREENSHOT: wxo-kb-upload-pdf.png]`

### Step 2.5 — Save and Index

Click **Create** (or **Save**) to submit the knowledge base. WXO will begin chunking and indexing the PDF document.

> 📸 **Screenshot placeholder:** Knowledge base creation in progress — status shown as "Indexing" or "Processing".
> `[SCREENSHOT: wxo-kb-indexing-status.png]`

### Step 2.6 — Wait for Indexing to Complete

The indexing process typically takes 1–3 minutes. Refresh the Knowledge Bases list page periodically until the `flight_ops_runbook` entry shows a status of **Ready** (or **Indexed**).

> 📸 **Screenshot placeholder:** Knowledge Bases list with `flight_ops_runbook` showing "Ready" / green status indicator.
> `[SCREENSHOT: wxo-kb-ready-status.png]`

> ⚠️ **Do not proceed to Part 3 until the knowledge base status is Ready.** An agent attached to an un-indexed knowledge base will be unable to retrieve runbook content.

---

## Part 3 — Create the Flight Triage Agent

### Step 3.1 — Navigate to Agents

From the left navigation sidebar, click **AI Builders** → **Agents**.

> 📸 **Screenshot placeholder:** Left nav with "Agents" highlighted under "AI Builders".
> `[SCREENSHOT: wxo-nav-agents.png]`

### Step 3.2 — Create a New Agent

Click the **New agent** button (top-right).

> 📸 **Screenshot placeholder:** Agents list page with the "New agent" button highlighted.
> `[SCREENSHOT: wxo-agents-list-new-button.png]`

### Step 3.3 — Set Agent Name and Description

In the agent creation form, fill in the **Name** and **Description** fields.

> ⚠️ **Important — Multi-Tenant Sharing:** All workshop participants share the same WXO tenant. You **must** append your initials to the agent name to avoid overwriting a colleague's work.

| Field | Value |
|---|---|
| **Name** | `flight_triage_agent_<initials>` (e.g., `flight_triage_agent_js`) |
| **Display Name** | `Flight Triage Agent (<INITIALS>)` (e.g., `Flight Triage Agent (JS)`) |
| **Description** | `Triages real-time flight schedule anomaly alerts from Confluent Kafka. Uses the Flight Operations Runbook knowledge base to produce structured recommendations and mitigation options for operational disruptions.` |

> 📸 **Screenshot placeholder:** New agent form with Name, Display Name, and Description fields filled in.
> `[SCREENSHOT: wxo-agent-create-name-desc.png]`

### Step 3.4 — Select the LLM

Scroll to the **Model** section. From the model dropdown, select:

```
groq/openai/gpt-oss-120b
```

If this model is not available on your tenant, ask your instructor for the recommended model name, or choose `watsonx/meta-llama/llama-3-3-70b-instruct` as an alternative.

> 📸 **Screenshot placeholder:** Agent form showing the Model dropdown with a model selected.
> `[SCREENSHOT: wxo-agent-model-selection.png]`

### Step 3.5 — Select Agent Style

In the **Style** section, choose:

```
react_core
```

> 📸 **Screenshot placeholder:** Agent style selection showing "react_core" selected.
> `[SCREENSHOT: wxo-agent-style-react-core.png]`

### Step 3.6 — Attach the Knowledge Base

Scroll to the **Knowledge Bases** section. Click **Add knowledge base** (or the `+` button).

From the list of available knowledge bases, select **`flight_ops_runbook`**.

> 📸 **Screenshot placeholder:** Knowledge base attachment panel showing `flight_ops_runbook` selected or appearing in the "Selected" list.
> `[SCREENSHOT: wxo-agent-kb-attach.png]`

Confirm `flight_ops_runbook` appears in the attached knowledge bases list.

> 📸 **Screenshot placeholder:** Agent form showing `flight_ops_runbook` in the knowledge base section as attached.
> `[SCREENSHOT: wxo-agent-kb-attached-confirmed.png]`

### Step 3.7 — Add Agent Instructions

Scroll to the **Instructions** section. Paste the full instruction block below into the text area:

```
You are an automated flight schedule anomaly processor. Never ask questions.
Respond only with the structured triage summary defined in step 6. Do not
attempt to call external tools or dispatch notifications directly.

The alert payload fields are:
  entity_id      Aircraft ID (e.g. N303AX) — use this as the lookup key
  stream         Always 'schedule' for this use case
  metric         One of: departure_delay | gate_wait | turnaround_time
  value          Observed windowed average
  unit           'minutes'
  anomaly_score  [0,1] — deviation relative to ARIMA confidence band
  hub            Hub airport (ORD or DFW)
  detected_at    ISO timestamp

Fleet reference:
  N101AX — B737-800, hub ORD, flight AX101, ORD→LAX
  N202AX — A320neo,  hub ORD, flight AX202, ORD→JFK
  N303AX — B737-MAX, hub DFW, flight AX303, DFW→MIA
  N404AX — A321XLR,  hub DFW, flight AX404, DFW→SEA

Severity mapping from anomaly_score:
  ≥ 0.9  CRITICAL
  ≥ 0.7  HIGH
  ≥ 0.5  MEDIUM
  else   LOW

ServiceNow urgency mapping:
  CRITICAL / HIGH  → urgency 1
  MEDIUM           → urgency 2
  LOW              → urgency 3

Processing steps — execute in order:

1. Extract all fields from the alert payload.

2. Derive the flight_number and route from entity_id using the fleet reference above.

3. Determine severity from anomaly_score using the table above.

4. Determine ServiceNow urgency using the mapping above.

5. Retrieve the matching section from the flight_ops_runbook knowledge base:
   - departure_delay → §2 Departure Delays
   - gate_wait       → §1 Gate Operations & Conflicts
   - turnaround_time → §3 Turnaround Time Disruptions
   Read the "Recommended Actions" block from the runbook and select the appropriate Option based on severity:
     CRITICAL/HIGH → Option A (immediate action)
     MEDIUM        → Option B (next-turn / scheduled adjustment)
     LOW           → Option C (monitor)

6. Return ONLY this structured summary block and stop:

   **Flight Triage Summary**
   - Flight: [flight_number]  Aircraft: [entity_id]  Hub: [hub]
   - Metric: [metric]  Value: [value] [unit]  Score: [anomaly_score]
   - Severity: [severity]  ServiceNow Urgency: [urgency]
   - Runbook Reference: [§section Option letter] — [option name]
   - Recommended Action: [action details from runbook]
   - Short Description for ServiceNow: "[severity] [flight_number] [metric] anomaly at [hub]"
```

> 📸 **Screenshot placeholder:** Instructions text area in the agent creation form with the full instruction block pasted in.
> `[SCREENSHOT: wxo-agent-instructions-pasted.png]`

### Step 3.8 — Leave Tools Empty

Scroll to the **Tools** section. Confirm it is empty — this agent intentionally uses no external tools and relies **only** on the knowledge base for its recommendations.

> 📸 **Screenshot placeholder:** Empty Tools section in the agent form.
> `[SCREENSHOT: wxo-agent-tools-empty.png]`

### Step 3.9 — Save and Deploy the Agent

Click **Save** (or **Create agent**) at the top-right or bottom of the form.

> 📸 **Screenshot placeholder:** Agent form Save/Create button highlighted.
> `[SCREENSHOT: wxo-agent-save-button.png]`

WXO will create the agent and return you to the Agents list. Confirm your agent (`flight_triage_agent_<initials>`) appears in the list.

> 📸 **Screenshot placeholder:** Agents list showing `flight_triage_agent_<initials>` as a new entry.
> `[SCREENSHOT: wxo-agent-list-confirmed.png]`

---

## Part 4 — Test Your Triage Agent in the WXO Chat

### Step 4.1 — Open the Agent's Chat Preview

Click your agent name (`flight_triage_agent_<initials>`) in the Agents list to open its detail page. Then click the **Preview** or **Test** button (typically shown in the top-right or as a chat panel on the right).

> 📸 **Screenshot placeholder:** Agent detail page with the Preview / Test chat panel visible on the right side.
> `[SCREENSHOT: wxo-agent-detail-preview.png]`

### Step 4.2 — Send a CRITICAL Alert (Gate Wait)

Paste the following anomaly alert payload into the chat input and press **Send**:

```
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

> 📸 **Screenshot placeholder:** Chat preview panel with the alert payload typed in the input box before sending.
> `[SCREENSHOT: wxo-chat-input-critical-alert.png]`

### Step 4.3 — Verify the Triage Response

The agent should respond with a structured summary. Verify the following are correct:

| Check | Expected Value |
|---|---|
| Flight mapping | `AX303` (DFW → MIA) |
| Severity | `CRITICAL` (anomaly_score 0.96 ≥ 0.9) |
| ServiceNow Urgency | `1` |
| Runbook section cited | `§1 Gate Operations & Conflicts` |
| Recommended option | `Option A` (immediate action) |
| Output format | Structured `**Flight Triage Summary**` block |

> 📸 **Screenshot placeholder:** Agent response in the chat panel showing the structured Flight Triage Summary with correct values for the N303AX CRITICAL gate_wait alert.
> `[SCREENSHOT: wxo-chat-response-critical.png]`

### Step 4.4 — Send a HIGH Alert (Departure Delay)

Send a second test alert to verify a different runbook section is retrieved:

```
Alert received:
- entity_id: N101AX
- stream: schedule
- metric: departure_delay
- value: 22.0
- unit: minutes
- anomaly_score: 0.75
- hub: ORD
- detected_at: 2026-09-30T17:15:00Z

Please triage this alert.
```

Verify the agent:
- Maps `N101AX` to **AX101** (ORD → LAX)
- Sets severity to **HIGH** (0.75 ≥ 0.7)
- Cites **§2 Departure Delays** from the runbook
- Selects **Option A** (anomaly_score ≥ 0.7 → CRITICAL/HIGH → Option A)

> 📸 **Screenshot placeholder:** Chat panel showing the second test alert and the agent's structured triage response for N101AX departure_delay HIGH.
> `[SCREENSHOT: wxo-chat-response-high-delay.png]`

### Step 4.5 — Send a LOW Alert (Turnaround Time)

Send a third test to exercise the lower-severity path:

```
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

Verify the agent:
- Maps `N404AX` to **AX404** (DFW → SEA)
- Sets severity to **LOW** (0.38 < 0.5)
- Cites **§3 Turnaround Time Disruptions** from the runbook
- Selects **Option C** (monitor)

> 📸 **Screenshot placeholder:** Chat panel showing the LOW severity turnaround_time response with §3 runbook reference and Option C selected.
> `[SCREENSHOT: wxo-chat-response-low-turnaround.png]`

---

## Part 5 — Explore Further (Optional)

Try these free-form questions to confirm the agent retrieves information directly from the PDF runbook:

```
What are the escalation triggers for departure delays under Section 2 of the runbook?
```

```
What is the procedure outlined in the runbook for a turnaround time anomaly exceeding 45 minutes at ORD?
```

```
Summarize all three operational disruption categories covered in the runbook and their recommended immediate actions.
```

> 📸 **Screenshot placeholder:** Chat panel showing one of the free-form runbook retrieval questions and the agent's grounded response.
> `[SCREENSHOT: wxo-chat-freeform-runbook-query.png]`

---

## Troubleshooting Reference

| Symptom | Likely Cause | Fix |
|---|---|---|
| Cannot log in to WXO | Incorrect tenant URL or expired credentials | Use the URL and credentials provided by the instructor |
| Knowledge base stuck in "Processing" | Large PDF or temporary backend delay | Wait 3–5 minutes and refresh the page |
| Knowledge base upload fails | File format or size issue | Ensure you are uploading the `.pdf` file, not the `.yaml` or `.md` |
| Agent cannot find runbook content | Knowledge base not yet in "Ready" state when agent was saved | Go back to the agent, detach and re-attach `flight_ops_runbook`, then save again |
| Agent gives generic responses without citing the runbook | Instructions not saved correctly | Edit the agent, re-paste the instructions, and save |
| Model not available in dropdown | LLM not provisioned on this tenant | Ask the instructor for the correct model name for your tenant |
| Agent name conflict ("already exists" error) | Another participant used the same initials | Use a longer suffix such as your full last name initial + first name initial |

---

## What You Accomplished

In this lab, you:

1. ✅ Logged into the watsonx Orchestrate browser UI
2. ✅ Created and indexed the `flight_ops_runbook` knowledge base from a PDF
3. ✅ Built a native `flight_triage_agent_<initials>` grounded in the runbook via RAG
4. ✅ Configured full processing instructions for anomaly severity mapping and structured output
5. ✅ Tested CRITICAL, HIGH, and LOW severity scenarios against all three runbook sections
6. ✅ Verified that the agent retrieves SOPs directly from the PDF — no hard-coded responses

**Lab complete.** You have deployed a production-style AI triage agent entirely through the WXO UI, with no code or CLI required.
