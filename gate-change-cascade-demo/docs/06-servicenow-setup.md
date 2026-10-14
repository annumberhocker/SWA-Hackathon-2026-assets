# Doc 06 — ServiceNow Setup _(optional)_

**Gate Change Cascade Demo — Optional Integration**

---

## Overview

> **This step is entirely optional.** The demo pipeline — Confluent → Flink → WXO Supervisor →
> Triage + Slack — runs end-to-end without it. Complete this guide only if you want to
> demonstrate WXO opening a ServiceNow incident as part of the anomaly response.

The `servicenow_agent` is provided by the **WXO catalog** as the built-in
**Request Manager in ServiceNow** agent. Bootstrap handles creating the OAuth password
connection automatically — you need to fill in two files before running it.

---

## Step 6.1 — Provision a ServiceNow PDI

1. Go to [developer.servicenow.com](https://developer.servicenow.com)
2. Sign in (or create a free account)
3. Click **Manage** → **Instance** → **Request Instance** → choose the latest release
4. Once provisioned, your instance URL looks like: `https://dev12345.service-now.com`
5. Note your admin credentials (shown once — copy immediately)

> 💡 PDI instances go to sleep after inactivity. Before a client demo, go to
> developer.servicenow.com → **Manage** → **Instance** → click **Wake Up** and wait ~2 minutes.

---

## Step 6.2 — Create an OAuth Client in ServiceNow

1. In your ServiceNow PDI, navigate to **System OAuth** → **Application Registry**
2. Click **New** → select **Create an OAuth API endpoint for external clients**
3. Fill in:
   - **Name**: `WXO Gate Change Cascade`
   - **Redirect URL**: `https://oauth.pstmn.io/v1/callback` _(placeholder — any valid URL)_
4. Click **Submit**
5. Open the record you just created — copy the **Client ID** and **Client Secret**

---

## Step 6.3 — Update `servicenow_connection.yaml`

Open [`orchestrate/connections/servicenow_connection.yaml`](../orchestrate/connections/servicenow_connection.yaml)
and replace `YOUR-PDI` with your actual PDI subdomain in both the `server_url` and `token_url`:

```yaml
environments:
  draft:
    kind: oauth_auth_password_flow
    type: team
    server_url: https://dev12345.service-now.com
    token_url: https://dev12345.service-now.com/oauth_token.do
```

---

## Step 6.4 — Fill in `.env`

Add to `.env`:
```env
SNOW_INSTANCE_URL=https://dev12345.service-now.com
SNOW_CLIENT_ID=<your-oauth-client-id>
SNOW_CLIENT_SECRET=<your-oauth-client-secret>
SNOW_USERNAME=admin
SNOW_PASSWORD=<your-admin-password>
```

---

## Step 6.5 — Run (or Re-run) Bootstrap

If bootstrap has already run, re-run it with `--reuse-env` to register the ServiceNow connection:

```bash
cd "$(git rev-parse --show-toplevel)/usecases/gate-change-cascade"
source .venv-orchestrate/bin/activate
cd orchestrate
bash bootstrap_env.sh --reuse-env
```

You should see:
```
=== Registering ServiceNow connection ===
  ✓ ServiceNow credentials set
```

---

## Step 6.6 — Add the Request Manager Agent from the WXO Catalog

1. In watsonx Orchestrate, open the left sidebar and click **Agent catalog**
2. Search for **Request Manager in ServiceNow**
3. Click the agent tile → click **Use as template**
4. Name the agent `servicenow_agent` (must match exactly — the supervisor references this name)
5. Click **Create**
6. Open the `servicenow_agent` → **Tools** → **Create Request in ServiceNow** → **Connectors** tab
7. Verify the `service-now` connection is listed and shows as configured

---

## Step 6.7 — Copy the Agent ID into `.env`

1. In watsonx Orchestrate open the `servicenow_agent`
2. The agent ID is in the browser URL: `.../agents/<agent-id>`

Add to `.env`:
```env
WO_SNOW_AGENT_ID=<agent-id>
```

---

## Step 6.8 — Add `servicenow_agent` as a Collaborator in the Supervisor Agent

1. In watsonx Orchestrate open `supervisor_agent`
2. Click **Collaborators** → **Add collaborator** → select `servicenow_agent`
3. Click **Save**

---

## Step 6.9 — Verify

Test the agent via the WXO chat UI by sending:
```
Open a test incident for flight AX303, gate_wait anomaly at DFW, severity HIGH
```

You should receive a response containing a `INCxxxxxxx` incident number.

Open your ServiceNow PDI at `https://dev12345.service-now.com/incident_list.do` to confirm.

---

**Return to:** [05-wxa-agents.md](05-wxa-agents.md)
