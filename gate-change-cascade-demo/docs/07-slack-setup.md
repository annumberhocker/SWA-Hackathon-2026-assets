# Doc 07 — Slack Setup

**Gate Change Cascade Demo — External System Setup**

---

## Overview

The `slack_agent` is provided by the **WXO catalog** as the built-in **Slack Messaging** agent.
Bootstrap handles creating the Slack OAuth2 connection automatically — you just need to fill in
two files before running it.

> 📖 **IBM official reference:** [Connecting to Slack — watsonx Orchestrate docs](https://www.ibm.com/docs/en/watsonx/watson-orchestrate/base?topic=channels-connecting-slack)
> Refer to that article for the latest IBM-recommended steps; this guide covers the same flow
> with the specific settings needed for this demo.

---

## Step 7.1 — Create a Slack App and Get OAuth Credentials

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click **Create New App** → **From scratch**
   - App Name: `Gate Change Cascade Alerts`
   - Workspace: select your demo workspace
3. In the left sidebar click **OAuth & Permissions**
4. Scroll to **Bot Token Scopes** → **Add an OAuth Scope** → add `chat:write`
5. Click **Install to Workspace** at the top → **Allow**
6. In the left sidebar click **Basic Information** → scroll to **App Credentials**
7. Copy the **Client ID** and **Client Secret**

---

## Step 7.2 — Fill in `.env`

Add to `.env`:
```env
SLACK_CLIENT_ID=<your-client-id>
SLACK_CLIENT_SECRET=<your-client-secret>
```

---

## Step 7.3 — Verify `slack_connection.yaml`

Open [`orchestrate/connections/slack_connection.yaml`](../orchestrate/connections/slack_connection.yaml).
The Slack OAuth2 URLs are already filled in — no changes needed unless your Slack workspace
uses a custom domain:

```yaml
environments:
  draft:
    kind: oauth_auth_code_flow
    type: team
    server_url: https://slack.com
    token_url: https://slack.com/api/oauth.v2.access
    authorization_url: https://slack.com/oauth/v2/authorize
```

---

## Step 7.4 — Get the Channel ID and Add to `.env`

1. In Slack, right-click your alerts channel (e.g. `#flight-ops-alerts`)
2. Click **View channel details** → scroll to the bottom of the **About** tab
3. Copy the **Channel ID** (starts with `C`)

Add to `.env`:
```env
SLACK_CHANNEL_ID=CXXXXXXXXXX
```

4. Invite the bot to the channel:
```
/invite @Gate Change Cascade Alerts
```

---

## Step 7.5 — Run Bootstrap

Bootstrap will import the connection config and set the OAuth2 credentials automatically:

```bash
cd "$(git rev-parse --show-toplevel)/usecases/gate-change-cascade"
source .venv-orchestrate/bin/activate
cd orchestrate
bash bootstrap_env.sh
```

You should see:
```
=== Registering Slack connection ===
  ✓ Slack credentials set
```

---

## Step 7.6 — Add the Slack Messaging Agent from the WXO Catalog

With the connection registered, set up the agent:

1. In watsonx Orchestrate, open the left sidebar and click **Agent catalog**
2. Search for **Slack Messaging**
3. Click the agent tile → click **Use as template**
4. Name the agent `slack_agent` (must match exactly — the supervisor references this name)
5. Click **Create**
6. Open the `slack_agent` → **Tools** → **Send a message in Slack** → **Connectors** tab
7. Verify the `slack` connection is listed and shows as configured

---

## Step 7.7 — Copy the Agent ID into `.env`

1. In watsonx Orchestrate open the `slack_agent`
2. The agent ID is in the browser URL: `.../agents/<agent-id>`

Add to `.env`:
```env
WO_SLACK_AGENT_ID=<agent-id>
```

---

## Step 7.8 — Add `slack_agent` as a Collaborator in the Supervisor Agent

1. In watsonx Orchestrate open `supervisor_agent`
2. Click **Collaborators** → **Add collaborator** → select `slack_agent`
3. Click **Save**

---

## Step 7.9 — Verify

```bash
curl -X POST https://slack.com/api/chat.postMessage \
    -H "Content-Type: application/json" \
    --data "{\"channel\": \"$SLACK_CHANNEL_ID\", \"text\": \"GCC smoke test — Slack connection verified.\"}"
```

> Note: this curl uses the app's bot token internally — if you want to test via curl directly,
> use the **Bot User OAuth Token** from OAuth & Permissions. The WXO connection uses OAuth2 auth code flow.

---

**Next:** [05-wxa-agents.md](05-wxa-agents.md)
