# Demo Script — Gate Change Cascade with Gmail Passenger Notification

**Audience:** Client / prospect  
**Duration:** ~12 minutes  
**Prerequisites:** Scenario 3 in [09-end-to-end-testing.md](09-end-to-end-testing.md) complete
and verified (Gmail authorized, supervisor instructions updated for passenger email)

---

## Setup Checklist (before the room fills up)

- [ ] `bash app-run-local.sh` running — simulator, alert consumer, dashboard all up
- [ ] Browser tab 1: Streamlit dashboard [http://localhost:8080](http://localhost:8080)
- [ ] Browser tab 2: watsonx Orchestrate UI — `supervisor_agent` chat open
- [ ] Browser tab 3: Gmail inbox for `GMAIL_RECIPIENT_ADDRESS`
- [ ] Browser tab 4: ServiceNow PDI `https://dev<number>.service-now.com/incident_list.do` _(if configured)_
- [ ] Run `python -m simulator.anomaly_injector --clear` to reset any prior injections
- [ ] Flink statement `gate-change-anomaly-detection` in **Running** state

> **Tip:** Keep the Streamlit dashboard and Gmail inbox side-by-side on screen so the audience
> can see the ops-side response and the passenger-side email at the same time.

---

## Act 1 — Set the Scene (1 min)

> _"What you're looking at is a real-time flight operations pipeline. On the left is the live
> Streamlit ops dashboard connected to a Confluent Kafka cluster. On the right is a Gmail inbox
> representing a passenger's email — think of it as the traveler sitting at their gate, phone
> in hand."_

> _"Right now, everything is normal. The simulator is generating flight schedule telemetry for
> four aircraft — two hubs, ORD and DFW — and streaming it into Kafka. Confluent Flink is
> watching those streams and running an ARIMA-based anomaly detection job in real time."_

> _"When Flink detects something unusual, it doesn't just log it. It triggers an AI agent
> pipeline powered by watsonx Orchestrate. And in about 60 seconds, we're going to see that
> entire chain fire — from the raw sensor event all the way to a passenger's inbox."_

---

## Act 2 — Inject the Anomaly (30 sec)

Switch to terminal. Say:

> _"I'm going to inject a departure delay anomaly on Flight AX202 — that's our A320neo out of
> O'Hare heading to JFK. 150 passengers. I'm going to spike the anomaly intensity to 5 —
> well above the HIGH threshold."_

```bash
python -m simulator.anomaly_injector AX202 schedule departure_delay --intensity 5.0
```

> _"Done. That one command pushed abnormal departure_delay telemetry into the Kafka topic.
> Flink is now computing the windowed z-score. Let's watch."_

Switch to the Streamlit dashboard.

---

## Act 3 — Flink Detection (1–2 min)

> _"Flink needs about one window cycle — roughly 90 seconds — to confirm the anomaly score
> crosses the threshold. You can see the live metric chart updating here."_

Point to the metric time-series panel.

> _"When the anomaly score hits 0.7 or above, the Flink job writes a record to the
> `ops-alerts` Kafka topic. Our alert consumer is subscribed to that topic and will
> immediately route the payload to the Supervisor Agent."_

While waiting, optionally show the Flink statement in Confluent Cloud UI or say:

> _"Behind the scenes Flink is running a continuous SQL query: a tumbling 90-second window,
> computing the mean and standard deviation of departure_delay values, and comparing them
> to a 30-day ARIMA baseline stored in a Confluent TableFlow Iceberg table. That's the
> historical layer — every event that's ever flowed through this Kafka topic is queryable
> as a structured table, no ETL pipeline required."_

---

## Act 4 — The Agent Pipeline Fires (2–3 min)

When the `ALERT` row appears in the Agent Activity panel, say:

> _"There it is. Flink detected the anomaly and the alert landed in the Supervisor Agent.
> Watch what happens next — this is the multi-agent orchestration step."_

As the `RESPONSE` appears, walk through it:

> _"The Supervisor Agent first delegated to the Flight Triage Agent. That agent made three
> tool calls:"_

Point to the triage summary on screen:

> **1. Live stream window** — _"It pulled the live 30-second pulse from Kafka: the current
> min, max, and average departure_delay for N202AX right now."_

> **2. 24-hour anomaly history** — _"It checked whether this flight has been anomalous
> before today — giving us frequency context, not just severity."_

> **3. TableFlow Iceberg query** — _"And here's where the historical baseline comes in.
> It queried 30 days of departure_delay data for Flight AX202 from the Iceberg table
> materialized by Confluent TableFlow. The current value is [X]x above the 30-day average —
> this isn't a one-off blip, it's a genuine operational anomaly."_

Point to the Runbook line:

> _"The triage agent also retrieved the matching section from the Flight Operations Runbook
> knowledge base — that's a RAG lookup. Because the severity is HIGH, it pulled §2 Option A:
> Full Escalation. The recommended action is right there in plain English."_

---

## Act 5 — The Passenger Email Arrives (30 sec)

Switch to the Gmail inbox tab (or have it visible alongside).

> _"Now here's the part that closes the loop for passengers. After triage completed, the
> Supervisor Agent composed and sent a delay notification email using the Gmail tool from the
> watsonx Orchestrate catalog."_

Open the email. Walk through it:

> _"Subject: **Flight AX202 Delay Notice — ORD, [today's date]**"_

> _"The body was generated by the agent using the triage output — the current delay value,
> the 30-day baseline, the severity, and the specific recommended action from the runbook.
> This is not a template fill-in. The agent wrote this from the structured triage summary."_

Read the key lines:

```
Dear Passenger,

We are writing to inform you that Flight AX202 departing from ORD is
currently experiencing a departure_delay delay.

Delay details:
  - Current departure_delay: 34 min (baseline: 12.4 min)
  - Severity: HIGH
  - Detected at: 2025-07-14T19:43:22Z

Our operations team is actively working on resolution.
Recommended action: Escalate to Duty Manager and initiate passenger communication.

We apologize for the inconvenience and will provide updates as the situation develops.

— AirX Operations
```

> _"150 passengers on that flight. In a real deployment this would fan out to all of them
> — or to a CRM system that handles the distribution. The agent just handled the detection,
> triage, runbook lookup, AND the outbound passenger communication in a single automated
> pipeline, with no human in the loop."_

---

## Act 6 — The Full Picture (2 min)

Switch to the Streamlit dashboard. Show the full `RESPONSE` block.

> _"Let's zoom out. Here's what just happened in about 90 seconds:"_

Walk through the pipeline verbally, pointing at each layer:

```
Kafka (flight telemetry)
  → Flink (ARIMA anomaly detection, 90s window)
    → ops-alerts topic
      → alert consumer
        → Supervisor Agent (watsonx Orchestrate)
            → flight_triage_agent
                → flight_stream_window (live Kafka)
                → recent_flight_anomalies (24h history)
                → query_flight_history (TableFlow / Iceberg 30d baseline)
                → flight_ops_runbook (RAG knowledge base)
            → gmail_agent (Send email with Gmail)
              → passenger inbox
```

> _"Every layer is real: the Kafka cluster is running in Confluent Cloud, the Flink job is
> continuous, the Iceberg table is live, and the email just landed in a real inbox. What
> makes this different from a scripted demo is that the agent is reasoning — it's choosing
> the right runbook option based on the actual anomaly score, and it's composing the email
> from the triage output, not from a hard-coded string."_

> _"This pattern — real-time event streaming plus AI-driven triage plus automated
> multi-channel notification — is what we call the Gate Change Cascade architecture.
> The same skeleton applies to any domain where you have high-velocity operational events
> and need both internal escalation and external stakeholder communication."_

---

## Act 7 — Q&A Primers

Use these if questions don't come naturally:

**"What if TableFlow isn't set up yet?"**
> _"The triage agent degrades gracefully — it still runs the live stream query and the 24h
> history check. The historical baseline line in the triage summary just reads 'TableFlow
> not configured'. The agent still produces a valid recommendation. Enabling TableFlow adds
> the Iceberg layer on top of what already works."_

**"Can you add ServiceNow too?"**
> _"Yes — it's the next optional layer. When `servicenow_agent` is added as a collaborator on
> the Supervisor, it opens a P1 incident automatically in your PDI. We can show that in the
> next scenario or set it up together after the demo."_

**"How does the agent know which runbook section to use?"**
> _"The Flight Triage Agent has a RAG knowledge base — the Flight Operations Runbook PDF.
> The agent instructions tell it to retrieve the section matching the anomaly metric
> (departure_delay → §2, gate_wait → §1, turnaround_time → §3) and pick the option based
> on severity. The LLM does the retrieval and the selection; the runbook provides the
> authoritative content."_

**"Could we customize the passenger email format?"**
> _"Absolutely. The email format lives in the Supervisor Agent's instructions — it's plain
> text that you edit in the WXO UI. You can change the tone, add a rebooking link, include
> a flight status URL, localize it — any instruction-level change takes effect immediately
> without redeploying anything."_

---

## Clean Up

```bash
python -m simulator.anomaly_injector --clear
```

> _"And that's the full loop. Anomaly cleared — the simulator returns to normal baseline and
> Flink stops flagging events for that flight."_

---

**Next step for the audience:** [09-end-to-end-testing.md](09-end-to-end-testing.md) — hands-on
walkthrough of all three scenarios including this one.
