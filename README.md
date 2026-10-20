# SWA Hackathon 2026 Assets

Assets for the **Hackathon Track: Streaming AI with IBM Bob, Confluent Cloud & watsonx Orchestrate**.

## Labs
Hands-on lab guides and supporting configuration for the hackathon workshop. Start with [`workshop-labs/README.md`](workshop-labs/README.md).

| Lab | File | Focus |
|---|---|---|
| Prerequisite | [`Install-Bob.md`](workshop-labs/Install-Bob.md) | Install IBM Bob IDE, sign in, verify MCP config |
| Lab 1 | [`WXO-No-Code.md`](workshop-labs/WXO-No-Code.md) | watsonx Orchestrate browser UI, knowledge base ingestion, flight triage agent |
| Lab 2 | [`Bob-and-WXO.md`](workshop-labs/Bob-and-WXO.md) | watsonx Orchestrate MCP/ADK, knowledge base ingestion, flight triage agent |
| Lab 3 | [`Bob-and-Confluent.md`](workshop-labs/Bob-and-Confluent.md) | Real-time stream processing — Confluent MCP, Kafka topics, Flink SQL anomaly detection |
| Lab 4 | [`WXO-Extraction-Flow.md`](workshop-labs/WXO-Extraction-Flow.md) | Document extraction — Work Order agent via WXO UI |


## WXO Integration Guides

Step-by-step guides for connecting third-party systems to watsonx Orchestrate as AI agents. Each guide is application-independent and includes OpenAPI tool definitions, authentication setup, agent instructions, test scenarios, and a collaborator wiring section.

| Guide | File | Integration method |
|---|---|---|
| ServiceNow | [`ServiceNow-Agent-WXO-Setup.md`](ServiceNow-Agent-WXO-Setup.md) | Built-in WXO app (App catalog → ServiceNow) |
| Databricks | [`Databricks-Agent-WXO-Setup.md`](Databricks-Agent-WXO-Setup.md) | Custom OpenAPI tools (Jobs API + SQL Statements API, Bearer PAT) |
| Salesforce | [`Salesforce-Agent-WXO-Setup.md`](Salesforce-Agent-WXO-Setup.md) | Custom OpenAPI tools (REST API, OAuth 2.0 Connected App) |


## Additional resources

- [Quick Start for Confluent Cloud](https://docs.confluent.io/cloud/current/get-started/index.html)
- [Confluent Developer HUB](https://developer.confluent.io/)
- [Kafka Event generator](https://shadowtraffic.io/)
- [Getting Started with watsonx Orchestrate](https://www.ibm.com/docs/en/watsonx/watson-orchestrate/base?topic=getting-started)
- [watsonx Orchestrate Control Plane Demo](https://www.youtube.com/watch?v=6aLhT6DMYt0)
- [watsonx Orchestrate Tutorials](https://developer.ibm.com/components/watsonx-orchestrate/tutorials/)
- [watsonx Orchestrate Learning Paths](https://developer.ibm.com/learningpaths/get-started-watsonx-orchestrate/)
- [Quick Start for Bob](https://bob.ibm.com/docs/ide/getting-started/quickstart)
- [Build with Bob](https://www.youtube.com/@BuildwithIBM)
- [Bob Tutorials](https://developer.ibm.com/components/ibm-bob/tutorials/)
- [IBM Developer HUB](https://developer.ibm.com/)
- [Digital Self-Serve Co-Create Experience](https://ibm.github.io/dsce-sample-apps/)
