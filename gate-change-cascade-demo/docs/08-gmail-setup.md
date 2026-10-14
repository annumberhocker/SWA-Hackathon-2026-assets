# Doc 08 — Gmail Setup _(optional)_

**Gate Change Cascade Demo — Optional Integration**

---

## Overview

> **This step is entirely optional.** Add it any time after bootstrap to enable the
> supervisor agent to send anomaly notification emails via Gmail in addition to (or instead of)
> Slack.

The Gmail **Send email with Gmail** tool comes from the WXO catalog. Bootstrap registers the
OAuth2 connection automatically — you need a Google Cloud OAuth app and your credentials
in `.env` before running it.

---

## Step 8.1 — Enable 2-Step Verification on your Google Account

1. Navigate to [myaccount.google.com/security](https://myaccount.google.com/security)
2. Confirm **2-Step Verification** is enabled — the Gmail OAuth flow requires it

> If you don't have it enabled, either enable it now or ask your instructor for shared credentials.

---

## Step 8.2 — Create a Google Cloud Project and Enable the Gmail API

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click **Select a project** → **New Project**
   - Project name: `wxo-project`
   - Click **Create**
3. Select your new project
4. In the left sidebar click **APIs & Services** → **Enable APIs and services**
5. Search for `Gmail API` → select it → click **Enable**

---

## Step 8.3 — Create an OAuth 2.0 Client

1. In the left sidebar click **APIs & Services** → **Credentials**
2. Click **Create credentials** → **OAuth client ID**
3. If prompted, click **Configure consent screen** first:
   - Click **Get started**
   - **App name**: `wxo-app`
   - **User support email**: your Gmail address → **Next**
   - **Audience**: select `External` → **Next**
   - **Contact email**: your Gmail address → **Next**
   - Check the agreement box → **Continue** → **Create**
4. Back in Credentials, click **Create credentials** → **OAuth client ID** again
5. Fill in:
   - **Application type**: `Web application`
   - **Name**: `wxo-app-client`
   - **Authorized redirect URIs** → **+ Add URI**:
     ```
     https://<region>.watson-orchestrate.cloud.ibm.com/mfe_connectors/api/v1/agentic/oauth/_callback
     ```
     Replace `<region>` with your WXO region (e.g. `us-south`, `ca-tor`, `eu-de`)
   - Click **Create**
6. Copy the **Client ID** and **Client Secret** — download the JSON for safe-keeping

---

## Step 8.4 — Add Your Account as a Test User

1. In the left sidebar click **Audience**
2. Click **Add users**
3. Enter the Gmail address you are using for this setup
4. Click **Save**

---

## Step 8.5 — Fill in `.env`

Add to `.env`:
```env
GMAIL_CLIENT_ID=<your-client-id>
GMAIL_CLIENT_SECRET=<your-client-secret>
GMAIL_SENDER_ADDRESS=<your-gmail-address>
GMAIL_RECIPIENT_ADDRESS=<alert-recipient-address>
```

---

## Step 8.6 — Run (or Re-run) Bootstrap

If bootstrap has already run, re-run it with `--reuse-env` to register the Gmail connection:

```bash
source .venv-orchestrate/bin/activate
cd orchestrate
bash bootstrap_env.sh --reuse-env --with-gmail
```

You should see:
```
=== Registering Gmail connection ===
  ✓ Gmail credentials set
```

---

## Step 8.7 — Add the Gmail Tool from the WXO Catalog

1. In watsonx Orchestrate open the agent you want to add Gmail to
   (e.g. `supervisor_agent` or a new dedicated email agent)
2. Click **Toolset** → **Add tool** → **Catalog**
3. On the left sidebar filter by **Tools**, search `google` under **Apps**
4. Scroll down and select **Send email with Gmail** → click **Add to Agent**

---

## Step 8.8 — Authorize the Gmail Connection

1. With the tool added, click **Edit details** on the **Send email with Gmail** tool
2. Click **Connectors** tab → **⋮** menu → **Edit connection**
3. Verify the following fields are populated (they come from the connection bootstrap registered):

| Field | Value |
|---|---|
| **Server URL** | `https://www.googleapis.com` |
| **Token URL** | `https://oauth2.googleapis.com/token` |
| **Authorization URL** | `https://accounts.google.com/o/oauth2/v2/auth` |
| **Client ID** | your client ID |
| **Client Secret** | your client secret |
| **Scope** | `https://www.googleapis.com/auth/gmail.send` |
| **Credential type** | Team credentials |

4. Click **Save Changes**
5. Click **Continue** to begin the OAuth authorization flow
6. Sign in with your Google account and grant the `gmail.send` permission

---

## Step 8.9 — Verify

Send a test email from the WXO chat UI:

```
Send a test email to <your-recipient-address> with subject "GCC smoke test" and body
"Gmail connection verified for Gate Change Cascade demo."
```

You should receive the email within a few seconds.

---

**Return to:** [05-wxa-agents.md](05-wxa-agents.md)
