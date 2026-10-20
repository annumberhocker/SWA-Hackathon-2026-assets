# Setting Up a Databricks Agent in watsonx Orchestrate

This guide walks you through connecting a Databricks workspace to watsonx Orchestrate (WXO) and building an AI agent that can run jobs, execute SQL, and query tables through natural language. Unlike ServiceNow, Databricks does not have a prebuilt WXO app — the integration is done by importing a custom OpenAPI tool definition that points at the Databricks REST API.

---

## What You Will Build

A **native AI agent** in watsonx Orchestrate that:
- Authenticates to a Databricks workspace using a Personal Access Token
- Can trigger job runs, poll run status, and execute SQL statements against a Databricks SQL warehouse
- Exposes those capabilities as WXO tools an agent can call on demand
- Is ready to be used standalone or wired as a collaborator into a supervisor agent

---

## How the Integration Works

```
WXO Agent
   │
   ├── custom tool: run_databricks_job       ──► POST /api/2.1/jobs/run-now
   ├── custom tool: get_job_run_status       ──► GET  /api/2.1/jobs/runs/get
   ├── custom tool: execute_sql_statement    ──► POST /api/2.0/sql/statements
   └── custom tool: get_sql_statement_result ──► GET  /api/2.0/sql/statements/{id}
             │
             ▼
     Databricks REST API
     (Bearer: Personal Access Token)
```

Each Databricks action becomes a WXO custom tool. The agent LLM decides which tool to call based on the user's natural language request.

---

## Prerequisites

| Requirement | Details |
|---|---|
| WXO tenant URL | Provided by your administrator (e.g. `https://<instance>.watson-orchestrate.ibm.com`) |
| WXO login credentials | IBMid or tenant-specific credentials with **Agent Builder** or **Admin** role |
| Databricks workspace URL | The base URL of your workspace (e.g. `https://<workspace-id>.azuredatabricks.net` or `https://<workspace-id>.cloud.databricks.com`) |
| Databricks Personal Access Token | A PAT generated in your Databricks workspace under **User Settings → Developer → Access tokens** |
| Databricks Job ID(s) | The integer Job ID(s) for any jobs you want the agent to trigger (found in the Jobs UI URL: `.../jobs/<job-id>`) |
| Databricks SQL Warehouse ID | The warehouse ID for SQL execution (found in the SQL Warehouses UI, **Connection details → HTTP path**) |
| Your initials | Used to namespace your agent name — all participants on a shared tenant must use unique names |

> **Databricks PAT permissions:** The token must belong to an account with CAN MANAGE RUN on the target jobs and CAN USE on the target SQL warehouse.

---

## Part 1 — Log In to watsonx Orchestrate

### Step 1.1 — Log In to IBM Cloud

Open a browser and navigate to the IBM Cloud URL provided in your environment email. Sign in with the credentials provided.

![IBM Cloud login page showing the IBMid sign-in form.](workshop-labs/images/Environment_Login.png)

### Step 1.2 — Open the Resource List

After logging in, click the **hamburger menu** (☰) in the top-left corner, then click **Resource list**.

![IBM Cloud top-left hamburger menu open with "Resource list" highlighted.](workshop-labs/images/Resource_List.png)

### Step 1.3 — Locate the watsonx Orchestrate Instance

In the Resource list, expand **AI / Machine Learning**. Find the watsonx Orchestrate row and click it.

![Resource list with "AI / Machine Learning" section expanded and watsonx Orchestrate highlighted.](workshop-labs/images/Choose_Orchestrate.png)

### Step 1.4 — Launch watsonx Orchestrate

Click **Launch watsonx Orchestrate**. You will land on the WXO home screen.

![watsonx Orchestrate service instance page with the "Launch" button highlighted.](workshop-labs/images/Launch_Orchestrate.png)

---

## Part 2 — Prepare the Databricks OpenAPI Tool Definitions

WXO custom tools are defined as OpenAPI 3.0 snippets. You will create one YAML file per Databricks action, then import each as a tool. A minimal working set for job orchestration and SQL execution is shown below.

> **Before you start:** Replace every occurrence of `<DATABRICKS_HOST>` with your workspace URL (e.g. `adb-123456789.0.azuredatabricks.net`).

### Tool 1 — `run_databricks_job`

Save the following as `databricks_run_job.yaml`:

```yaml
openapi: 3.0.0
info:
  title: Databricks Run Job
  version: "1.0"
servers:
  - url: https://<DATABRICKS_HOST>
paths:
  /api/2.1/jobs/run-now:
    post:
      operationId: run_databricks_job
      summary: Trigger a Databricks job run
      description: >
        Submits a run for the specified Databricks job. Returns the run_id
        which can be used to poll status with get_job_run_status.
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - job_id
              properties:
                job_id:
                  type: integer
                  description: The integer ID of the job to run.
                notebook_params:
                  type: object
                  description: >
                    Optional key-value parameters to pass to the notebook.
                    Keys and values must be strings.
                  additionalProperties:
                    type: string
      responses:
        "200":
          description: Run submitted successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  run_id:
                    type: integer
                    description: The ID of the newly created run.
      security:
        - bearerAuth: []
components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
```

### Tool 2 — `get_job_run_status`

Save the following as `databricks_get_run.yaml`:

```yaml
openapi: 3.0.0
info:
  title: Databricks Get Job Run Status
  version: "1.0"
servers:
  - url: https://<DATABRICKS_HOST>
paths:
  /api/2.1/jobs/runs/get:
    get:
      operationId: get_job_run_status
      summary: Get the status of a Databricks job run
      description: >
        Retrieves the current state of a job run by run_id.
        life_cycle_state values: PENDING, RUNNING, TERMINATING, TERMINATED, SKIPPED, INTERNAL_ERROR.
        result_state values (terminal only): SUCCESS, FAILED, TIMEDOUT, CANCELED.
      parameters:
        - name: run_id
          in: query
          required: true
          schema:
            type: integer
          description: The run_id returned by run_databricks_job.
      responses:
        "200":
          description: Run details
          content:
            application/json:
              schema:
                type: object
                properties:
                  run_id:
                    type: integer
                  state:
                    type: object
                    properties:
                      life_cycle_state:
                        type: string
                      result_state:
                        type: string
                      state_message:
                        type: string
      security:
        - bearerAuth: []
components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
```

### Tool 3 — `execute_sql_statement`

Save the following as `databricks_execute_sql.yaml`:

```yaml
openapi: 3.0.0
info:
  title: Databricks Execute SQL Statement
  version: "1.0"
servers:
  - url: https://<DATABRICKS_HOST>
paths:
  /api/2.0/sql/statements:
    post:
      operationId: execute_sql_statement
      summary: Execute a SQL statement on a Databricks SQL warehouse
      description: >
        Submits a SQL statement for execution against a Databricks SQL warehouse.
        Returns a statement_id for polling results.
        Set wait_timeout to "0s" for async; use "30s" for synchronous (returns
        results inline if the query finishes within 30 seconds).
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - warehouse_id
                - statement
              properties:
                warehouse_id:
                  type: string
                  description: The SQL warehouse ID (from Connection details → HTTP path).
                statement:
                  type: string
                  description: The SQL statement to execute.
                wait_timeout:
                  type: string
                  description: >
                    How long to wait for results inline. Use "0s" to get a
                    statement_id immediately, or "30s" to wait up to 30 seconds.
                  default: "30s"
                catalog:
                  type: string
                  description: Optional Unity Catalog catalog name.
                schema:
                  type: string
                  description: Optional schema (database) name.
      responses:
        "200":
          description: Statement submitted
          content:
            application/json:
              schema:
                type: object
                properties:
                  statement_id:
                    type: string
                  status:
                    type: object
                    properties:
                      state:
                        type: string
                        description: PENDING, RUNNING, SUCCEEDED, FAILED, CANCELED, CLOSED
                  result:
                    type: object
                    description: Inline result rows if the statement completed within wait_timeout.
      security:
        - bearerAuth: []
components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
```

### Tool 4 — `get_sql_statement_result`

Save the following as `databricks_get_sql_result.yaml`:

```yaml
openapi: 3.0.0
info:
  title: Databricks Get SQL Statement Result
  version: "1.0"
servers:
  - url: https://<DATABRICKS_HOST>
paths:
  /api/2.0/sql/statements/{statement_id}:
    get:
      operationId: get_sql_statement_result
      summary: Retrieve the result of a SQL statement execution
      description: >
        Polls a previously submitted SQL statement for its status and result rows.
        Call this after execute_sql_statement returns a statement_id whose status
        is not yet SUCCEEDED.
      parameters:
        - name: statement_id
          in: path
          required: true
          schema:
            type: string
          description: The statement_id returned by execute_sql_statement.
      responses:
        "200":
          description: Statement result
          content:
            application/json:
              schema:
                type: object
                properties:
                  statement_id:
                    type: string
                  status:
                    type: object
                    properties:
                      state:
                        type: string
                  result:
                    type: object
                    description: Result rows and schema when state is SUCCEEDED.
      security:
        - bearerAuth: []
components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
```

---

## Part 3 — Import the Tools into WXO

### Step 3.1 — Open Tools Management

From the WXO home screen, navigate to **Tools** (in the left sidebar or from the **Build** menu, depending on your WXO version).

### Step 3.2 — Create a New Custom Tool

Click **Create tool** → **From file** (or **Import OpenAPI**).

### Step 3.3 — Upload and Configure the First Tool

Upload `databricks_run_job.yaml`. WXO will parse the spec and show you the operation details.

In the **Authentication** section, select **Bearer token** and enter your Databricks Personal Access Token:

```
Authorization: Bearer <your-databricks-pat>
```

> **Security note:** WXO stores the bearer token as an encrypted secret attached to this tool definition. It is not visible after saving.

Click **Save tool**.

### Step 3.4 — Repeat for Each Remaining Tool

Repeat Step 3.2–3.3 for each remaining YAML file:

| File | Tool created |
|---|---|
| `databricks_get_run.yaml` | `get_job_run_status` |
| `databricks_execute_sql.yaml` | `execute_sql_statement` |
| `databricks_get_sql_result.yaml` | `get_sql_statement_result` |

Set the same Databricks PAT as the bearer token for each tool.

> All four tools are now available in your WXO tenant's tool library and can be added to any agent.

---

## Part 4 — Create the Databricks Agent

### Step 4.1 — Start a New Agent

From the WXO home screen, click **Create Agent** (top-right corner).

![Home screen with Create Agent button highlighted.](workshop-labs/images/Home_Create_Agent.png)

### Step 4.2 — Create from Scratch

Click **Create from scratch**.

![Create agent options with "Create from scratch" highlighted.](workshop-labs/images/Create_From_Scratch.png)

### Step 4.3 — Fill In Agent Name, Description, and Instructions

> ⚠️ **Multi-Tenant Sharing:** If you share a WXO tenant with others, **append your initials** to the agent name to avoid collisions.

**Agent Name:**
```
databricks_agent_<initials>
```

**Description:**
```
Triggers Databricks job runs, monitors run status, and executes SQL queries against Databricks SQL warehouses through natural language requests.
```

**Instructions:** paste the full block below into the Instructions field and fill in the bracketed sections for your workspace:

```
You are a Databricks operations assistant. You interact with a Databricks workspace
on behalf of the user by calling the available tools.

Available tools and when to use them:
- run_databricks_job       → When the user asks to run, trigger, or start a job.
- get_job_run_status       → When the user asks for the status, progress, or result of a run.
- execute_sql_statement    → When the user asks to query data, run SQL, or retrieve a table.
- get_sql_statement_result → When execute_sql_statement returns a pending statement_id.

Rules:
- Never ask clarifying questions if you have enough information to act.
- Always include the run_id or statement_id in your response so the user can track the operation.
- When running a job, confirm the job_id before triggering if it was not explicitly provided.
- When executing SQL, use the default warehouse_id: <YOUR_WAREHOUSE_ID>.
- If the SQL result has more than 20 rows, summarise the results rather than listing every row.
- If a tool call fails, report the HTTP status and error message clearly.
- Do not infer or fabricate job IDs, run IDs, or query results.

Known job IDs (update this list for your workspace):
  [job_name]  → job_id: [integer]
  Example:
  daily_etl   → job_id: 12345
  data_quality_check → job_id: 67890
```

---

## Part 5 — Add the Databricks Tools to the Agent

### Step 5.1 — Open the Tools Tab

From within the agent editor, click the **Tools** tab.

### Step 5.2 — Add Each Custom Tool

Click **Add tool** → **Custom tools** (or **My tools**). Select the four Databricks tools you imported in Part 3:

- `run_databricks_job`
- `get_job_run_status`
- `execute_sql_statement`
- `get_sql_statement_result`

Click **Add** to attach them to the agent.

### Step 5.3 — Save the Agent

Click **Save**.

---

## Part 6 — Test the Agent in Draft Preview

### Step 6.1 — Trigger a Job Run

Paste the following into the draft preview chat and press **Enter** (replace `12345` with a real job ID in your workspace):

```
Run Databricks job 12345 with parameter env=staging.
```

**Expected behaviour:**
- Agent calls `run_databricks_job` with `job_id: 12345` and `notebook_params: {"env": "staging"}`
- Returns the `run_id`, e.g. `Run submitted. run_id: 78901`

### Step 6.2 — Check Job Run Status

```
What is the status of run 78901?
```

**Expected behaviour:**
- Agent calls `get_job_run_status` with `run_id: 78901`
- Returns `life_cycle_state` (e.g. RUNNING) and `result_state` if terminal (e.g. SUCCESS)

### Step 6.3 — Execute a SQL Query

```
Query the top 10 rows from the sales.orders table where order_date > '2026-01-01'.
```

**Expected behaviour:**
- Agent calls `execute_sql_statement` with an appropriate SQL string and your warehouse ID
- If `wait_timeout: "30s"` and the query is fast, results come back inline
- If results are pending, agent notes the `statement_id` and you can ask for the result explicitly

### Step 6.4 — Retrieve Pending SQL Results

```
Get the results for statement abc-123.
```

**Expected behaviour:**
- Agent calls `get_sql_statement_result` with `statement_id: "abc-123"`
- Returns the result rows or reports the current state if still running

---

## Part 7 — Wire the Databricks Agent as a Collaborator (Optional)

If you have a supervisor agent that decides *when* to run a Databricks job or fetch data (e.g. an ops agent that reacts to anomaly alerts), register the Databricks agent as a **collaborator tool**.

### Step 7.1 — Open Your Supervisor Agent

Navigate to your existing supervisor agent and open it in the editor.

### Step 7.2 — Add the Databricks Agent as a Collaborator

Click **Tools** tab → **Add tool** → **Agent as tool**.

Select `databricks_agent_<initials>` and click **Add**.

### Step 7.3 — Update the Supervisor Instructions

Add a delegation rule, for example:

```
When the user asks for fresh data or needs a pipeline to run before analysis,
delegate to databricks_agent_<initials>. Pass the job name or SQL query as
a natural language request. Wait for the job run_id or query result before
continuing with your analysis.
```

---

## Troubleshooting Reference

| Symptom | Likely Cause | Fix |
|---|---|---|
| Tool import fails with "invalid spec" | YAML syntax error or missing required field | Validate your YAML at [editor.swagger.io](https://editor.swagger.io) before importing |
| Tool returns HTTP 401 Unauthorized | PAT expired, revoked, or entered incorrectly | Regenerate the PAT in Databricks under **User Settings → Developer → Access tokens** and update the tool's bearer token |
| Tool returns HTTP 403 Forbidden | PAT account lacks permissions on the job or warehouse | Grant CAN MANAGE RUN (for jobs) or CAN USE (for SQL warehouses) to the PAT account in Databricks |
| `execute_sql_statement` returns `state: FAILED` | SQL syntax error or table does not exist | Check the `error.message` field in the response and correct the SQL |
| Agent picks wrong job ID | Instructions list is missing or outdated | Add the correct `[job_name] → job_id` mapping to the agent instructions |
| Agent never calls `get_sql_statement_result` | LLM resolves inline if `wait_timeout` is non-zero | Set `wait_timeout: "0s"` in the OpenAPI spec default to force async; or keep `"30s"` for short queries |
| Workspace URL is unreachable from WXO | Network / firewall policy | Ensure your Databricks workspace allows inbound connections from IBM Cloud egress IPs (consult your WXO tenant's egress IP documentation) |
| Collaborator agent not invoked by supervisor | Delegation rule too vague | Add explicit trigger conditions to the supervisor instructions (e.g. "when the user mentions 'run pipeline' or 'query data'") |

---

## What You Accomplished

In this guide, you:

1. ✅ Created four Databricks OpenAPI tool definitions covering job runs, run status, SQL execution, and SQL result retrieval
2. ✅ Imported those tools into WXO with Databricks Personal Access Token authentication
3. ✅ Built a native Databricks agent with domain-appropriate instructions
4. ✅ Tested job trigger, status polling, and SQL query flows in the WXO draft preview
5. ✅ (Optional) Wired the Databricks agent as a collaborator in a supervisor agent for automated pipeline delegation

The four tools are reusable across any WXO agent on your tenant — import once, delegate from as many orchestration flows as you need.
