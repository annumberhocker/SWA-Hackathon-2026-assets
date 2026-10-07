# SWA Hackathon 2026 Assets

Assets for the **Hackathon Track: Streaming AI with IBM Bob, Confluent Cloud & watsonx Orchestrate**.

---

## Repository Structure

```
SWA-Hackathon-2026-assets/
├── flight-event-simulator/   # Kafka producer — simulates live flight telemetry
└── workshop-labs/            # Step-by-step hands-on lab guides and configuration
```

---

## `flight-event-simulator`

A Python Kafka producer that streams simulated flight schedule metrics to a Confluent Cloud topic (`flight-events`). Every 2 seconds it emits events for 4 aircraft across 3 metrics: `departure_delay`, `gate_wait`, and `turnaround_time`.

This simulator provides the live data feed consumed by the workshop labs — instructor or participants start it before running the Flink anomaly detection jobs in Lab 1.

**Quick start:**

```bash
cd flight-event-simulator
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp env.example .env   # fill in your Confluent Cloud credentials
python flight_producer.py
```

See [`flight-event-simulator/README.md`](flight-event-simulator/README.md) for full setup instructions.

---

## `workshop-labs`

Hands-on lab guides and supporting configuration for the hackathon workshop. Start with [`START_HERE.md`](workshop-labs/START_HERE.md).

### Labs

| Lab | File | Focus |
|---|---|---|
| Prerequisite | [`Install-Bob.md`](workshop-labs/Install-Bob.md) | Install IBM Bob IDE, sign in, verify MCP config |
| Lab 1 | [`Bob-and-Confluent.md`](workshop-labs/Bob-and-Confluent.md) | Real-time stream processing — Confluent MCP, Kafka topics, Flink SQL anomaly detection |
| Lab 2 | [`Bob-and-WXO.md`](workshop-labs/Bob-and-WXO.md) | Agentic AI — watsonx Orchestrate MCP, knowledge base ingestion, flight triage agent |
| Lab 2 (No-Code) | [`WXO-No-Code.md`](workshop-labs/WXO-No-Code.md) | Same as Lab 2 via the WXO browser UI — no CLI required |
| Lab 3 | [`WXO-Extraction-Flow.md`](workshop-labs/WXO-Extraction-Flow.md) | Document extraction — Work Order agent via WXO UI |

### Key Files

| File | Purpose |
|---|---|
| [`env.example`](workshop-labs/env.example) | Annotated example showing all required variables |
| [`INSTRUCTOR-SETUP.md`](workshop-labs/INSTRUCTOR-SETUP.md) | Guide for instructors to prepare and distribute `env.lab` before the workshop |
| [`mcp-confluent.json`](workshop-labs/mcp-confluent.json) | MCP server config for Confluent Cloud |
| [`mcp-wxo.json`](workshop-labs/mcp-wxo.json) | MCP server config for watsonx Orchestrate |
| [`flink/`](workshop-labs/flink/) | Flink SQL statements used in Lab 1 |
| [`orchestrate/`](workshop-labs/orchestrate/) | Agent YAML and knowledge base files used in Lab 2 |
