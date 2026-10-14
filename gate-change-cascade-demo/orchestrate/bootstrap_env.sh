#!/usr/bin/env bash
# Bootstrap the watsonx Orchestrate environment for Gate Change Cascade.
# Imports connections, tools, knowledge base, and the flight_triage + supervisor agents.
#
# Before running:
#   1. Fill in .env with WO_INSTANCE and WO_API_KEY (required)
#   2. (Optional) Slack:       complete docs/07-slack-setup.md then fill SLACK_CLIENT_ID/SECRET in .env
#   3. (Optional) ServiceNow:  complete docs/06-servicenow-setup.md then fill SNOW_* vars in .env
#   4. (Optional) Gmail:       complete docs/08-gmail-setup.md then fill GMAIL_* vars in .env
#
# All three catalog agents (Slack, ServiceNow, Gmail) are optional.
# The core demo runs fully with only flight_triage_agent + supervisor_agent.
# Agents are set up manually from the WXO catalog after bootstrap:
#   Slack:        docs/07-slack-setup.md (optional)
#   ServiceNow:   docs/06-servicenow-setup.md (optional)
#   Gmail:        docs/08-gmail-setup.md (optional)
#
# Usage:
#   ./bootstrap_env.sh                    # interactive — prompts for each connection
#   ./bootstrap_env.sh -r / --reuse-env   # re-run — skips 'env add'
#   ./bootstrap_env.sh --with-slack       # include Slack without prompting
#   ./bootstrap_env.sh --skip-slack       # skip Slack without prompting
#   ./bootstrap_env.sh --with-servicenow  # include ServiceNow without prompting
#   ./bootstrap_env.sh --skip-servicenow  # skip ServiceNow without prompting
#   ./bootstrap_env.sh --with-gmail       # include Gmail without prompting
#   ./bootstrap_env.sh --skip-gmail       # skip Gmail without prompting
set -euo pipefail

REUSE_ENV=false
SLACK_OPT=prompt    # prompt | yes | no
SNOW_OPT=prompt     # prompt | yes | no
GMAIL_OPT=prompt    # prompt | yes | no

while [[ $# -gt 0 ]]; do
    case "$1" in
        -r|--reuse-env)
            REUSE_ENV=true
            shift
            ;;
        --with-slack)
            SLACK_OPT=yes
            shift
            ;;
        --skip-slack)
            SLACK_OPT=no
            shift
            ;;
        --with-servicenow)
            SNOW_OPT=yes
            shift
            ;;
        --skip-servicenow)
            SNOW_OPT=no
            shift
            ;;
        --with-gmail)
            GMAIL_OPT=yes
            shift
            ;;
        --skip-gmail)
            GMAIL_OPT=no
            shift
            ;;
        -h|--help)
            sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "ERROR: unknown option '$1'" >&2
            exit 2
            ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="${ROOT_DIR}/.env"
ENV_EXAMPLE="${ROOT_DIR}/.env.example"
ADK_ENV_NAME="${WO_ADK_ENV_NAME:-gate-change-cascade}"
BUNDLE_DIR="${SCRIPT_DIR}/tools/manifest-bundle"
CONNECTIONS_DIR="${SCRIPT_DIR}/connections"

# ── Require orchestrate CLI ───────────────────────────────────────────────────
ORCHESTRATE="$(command -v orchestrate)" || {
    echo "ERROR: 'orchestrate' CLI not found on PATH."
    echo "       Install it with: pip install ibm-watsonx-orchestrate"
    exit 1
}

# ── Load .env ─────────────────────────────────────────────────────────────────
[ -f "$ENV_FILE" ] && { set -a; . "$ENV_FILE"; set +a; }

if [ -z "${WO_INSTANCE:-}" ] || [ -z "${WO_API_KEY:-}" ]; then
    echo "ERROR: WO_INSTANCE and WO_API_KEY must be set in ${ENV_FILE}"
    exit 1
fi

# ── Create / activate ADK environment ────────────────────────────────────────
echo "=== Configuring ADK environment '${ADK_ENV_NAME}' ==="
if [ "$REUSE_ENV" = "true" ]; then
    echo "  --reuse-env: skipping 'env add'"
else
    if ! "$ORCHESTRATE" env add -n "$ADK_ENV_NAME" -u "$WO_INSTANCE" --type ibm_iam 2>&1 \
            | tee /tmp/gcc_env_add.log; then
        grep -qiE 'exist|already' /tmp/gcc_env_add.log || { cat /tmp/gcc_env_add.log; exit 1; }
    fi
    rm -f /tmp/gcc_env_add.log
fi
"$ORCHESTRATE" env activate "$ADK_ENV_NAME" --api-key "$WO_API_KEY"

# ── Prompt for connections (if not decided by flags) ─────────────────────────
if [ "$SLACK_OPT" = "prompt" ]; then
    printf "Set up Slack connection? (optional) [y/N] "
    read -r _reply
    case "$_reply" in
        [yY]|[yY][eE][sS]) SLACK_OPT=yes ;;
        *)                  SLACK_OPT=no  ;;
    esac
fi

if [ "$SNOW_OPT" = "prompt" ]; then
    printf "Set up ServiceNow connection? (optional) [y/N] "
    read -r _reply
    case "$_reply" in
        [yY]|[yY][eE][sS]) SNOW_OPT=yes ;;
        *)                  SNOW_OPT=no  ;;
    esac
fi

if [ "$GMAIL_OPT" = "prompt" ]; then
    printf "Set up Gmail connection? (optional) [y/N] "
    read -r _reply
    case "$_reply" in
        [yY]|[yY][eE][sS]) GMAIL_OPT=yes ;;
        *)                  GMAIL_OPT=no  ;;
    esac
fi

# ── Register Slack connection ─────────────────────────────────────────────────
if [ "$SLACK_OPT" = "yes" ]; then
    echo "=== Registering Slack connection ==="
    "$ORCHESTRATE" connections import --file "${CONNECTIONS_DIR}/slack_connection.yaml" \
        2>/dev/null || echo "  (Slack connection already exists — skipping import)"
    if [ -n "${SLACK_CLIENT_ID:-}" ] && [ -n "${SLACK_CLIENT_SECRET:-}" ]; then
        "$ORCHESTRATE" connections set-credentials \
            --app-id slack \
            --environment draft \
            --kind oauth_auth_code_flow \
            --type team \
            --client-id     "$SLACK_CLIENT_ID" \
            --client-secret "$SLACK_CLIENT_SECRET" \
            2>/dev/null && echo "  ✓ Slack credentials set" \
            || echo "  ⚠ Slack credentials could not be set — check SLACK_CLIENT_ID / SLACK_CLIENT_SECRET in .env"
    else
        echo "  ⚠ SLACK_CLIENT_ID or SLACK_CLIENT_SECRET not set — skipping credential upload."
        echo "    Fill in .env and re-run with: bash bootstrap_env.sh --reuse-env --with-slack"
    fi
else
    echo "  Skipping Slack connection."
fi

# ── Register ServiceNow connection ────────────────────────────────────────────
if [ "$SNOW_OPT" = "yes" ]; then
    echo "=== Registering ServiceNow connection ==="
    "$ORCHESTRATE" connections import --file "${CONNECTIONS_DIR}/servicenow_connection.yaml" \
        2>/dev/null || echo "  (ServiceNow connection already exists — skipping import)"
    if [ -n "${SNOW_CLIENT_ID:-}" ] && [ -n "${SNOW_CLIENT_SECRET:-}" ] \
        && [ -n "${SNOW_USERNAME:-}" ] && [ -n "${SNOW_PASSWORD:-}" ]; then
        "$ORCHESTRATE" connections set-credentials \
            --app-id service-now \
            --environment draft \
            --kind oauth_auth_password_flow \
            --type team \
            --client-id     "$SNOW_CLIENT_ID" \
            --client-secret "$SNOW_CLIENT_SECRET" \
            --username      "$SNOW_USERNAME" \
            --password      "$SNOW_PASSWORD" \
            2>/dev/null && echo "  ✓ ServiceNow credentials set" \
            || echo "  ⚠ ServiceNow credentials could not be set — check SNOW_* vars in .env"
    else
        echo "  ⚠ SNOW_CLIENT_ID/SECRET/USERNAME/PASSWORD not set — skipping credential upload."
        echo "    Fill in .env and re-run with: bash bootstrap_env.sh --reuse-env --with-servicenow"
    fi
else
    echo "  Skipping ServiceNow connection."
fi

# ── Register Gmail connection ─────────────────────────────────────────────────
if [ "$GMAIL_OPT" = "yes" ]; then
    echo "=== Registering Gmail connection ==="
    "$ORCHESTRATE" connections import --file "${CONNECTIONS_DIR}/gmail_connection.yaml" \
        2>/dev/null || echo "  (Gmail connection already exists — skipping import)"
    if [ -n "${GMAIL_CLIENT_ID:-}" ] && [ -n "${GMAIL_CLIENT_SECRET:-}" ]; then
        "$ORCHESTRATE" connections set-credentials \
            --app-id gmail \
            --environment draft \
            --kind oauth_auth_code_flow \
            --type team \
            --client-id     "$GMAIL_CLIENT_ID" \
            --client-secret "$GMAIL_CLIENT_SECRET" \
            --scope         "https://www.googleapis.com/auth/gmail.send" \
            2>/dev/null && echo "  ✓ Gmail credentials set" \
            || echo "  ⚠ Gmail credentials could not be set — check GMAIL_CLIENT_ID / GMAIL_CLIENT_SECRET in .env"
    else
        echo "  ⚠ GMAIL_CLIENT_ID or GMAIL_CLIENT_SECRET not set — skipping credential upload."
        echo "    Fill in .env and re-run with: bash bootstrap_env.sh --reuse-env --with-gmail"
    fi
else
    echo "  Skipping Gmail connection."
fi

# ── Catalog agents: set up manually in WXO after bootstrap ────────────────────
echo "  NOTE: Slack agent — set up from the WXO catalog (see docs/07-slack-setup.md)"
echo "  NOTE: ServiceNow agent — set up from the WXO catalog (see docs/06-servicenow-setup.md, optional)"
echo "  NOTE: Gmail agent — set up from the WXO catalog (see docs/08-gmail-setup.md, optional)"

# ── Build manifest SQLite if needed ──────────────────────────────────────────
if [ ! -f "${BUNDLE_DIR}/flight_manifest.sqlite" ]; then
    echo "=== Building flight_manifest.sqlite ==="
    bash "${BUNDLE_DIR}/build.sh"
fi

# ── Stage tools — bake in INVESTIGATOR_API_URL at import time ────────────────
TOOL_STAGE="$(mktemp -d)"
trap 'rm -rf "$TOOL_STAGE"' EXIT

sed_escape() { printf '%s' "$1" | sed -e 's|[\\|&]|\\&|g'; }
API=$(sed_escape "${INVESTIGATOR_API_URL:-}")

stage_tool() {
    local src="${SCRIPT_DIR}/tools/$1"
    local dst="${TOOL_STAGE}/$1"
    cp "$src" "$dst"
    sed -i.bak -e "s|__INVESTIGATOR_API_URL__|${API}|g" "$dst" && rm -f "${dst}.bak"
    echo "$dst"
}

# ── Import single-file tools ──────────────────────────────────────────────────
echo "=== Importing single-file tools ==="
for t in flight_stream_window.py recent_flight_anomalies.py query_flight_history.py; do
    staged="$(stage_tool "$t")"
    echo "  import $t"
    "$ORCHESTRATE" tools import --kind python --file "$staged"
done

# ── Knowledge base ────────────────────────────────────────────────────────────
echo "=== Importing knowledge base ==="
KB_DIR="${SCRIPT_DIR}/knowledge-bases"
RUNBOOK_PDF="${KB_DIR}/flight_ops_runbook.pdf"

if [ -f "${RUNBOOK_PDF}" ]; then
    ( cd "${KB_DIR}" && "$ORCHESTRATE" knowledge-bases import --file flight_ops_runbook.yaml )
else
    echo "  NOTE: ${RUNBOOK_PDF} not found — skipping knowledge-base import."
    echo "        Generate it with: pandoc knowledge-bases/flight_ops_runbook.md -o ${RUNBOOK_PDF}"
    echo "        Then re-run: bash bootstrap_env.sh --reuse-env"
fi

# ── Import agents ─────────────────────────────────────────────────────────────
echo "=== Importing agents ==="
echo "  import flight_triage_agent.yaml"
"$ORCHESTRATE" agents import --file "${SCRIPT_DIR}/agents/flight_triage_agent.yaml"
echo "  NOTE: slack_agent — optional, set up from the WXO catalog (see docs/07-slack-setup.md)"
echo "  NOTE: servicenow_agent — optional, set up from the WXO catalog (see docs/06-servicenow-setup.md)"
echo "  import supervisor_agent.yaml"
"$ORCHESTRATE" agents import --file "${SCRIPT_DIR}/agents/supervisor_agent.yaml"

# ── Resolve agent IDs and write to .env ──────────────────────────────────────
# 'orchestrate agents list -v' returns {"native":[...],"assistant":[...],"external":[...]}
AGENTS_JSON="$("$ORCHESTRATE" agents list -v 2>/dev/null || echo '{}')"

resolve_id() {
    echo "$AGENTS_JSON" | python3 -c "
import sys, json
data = json.load(sys.stdin)
# flatten all agent kinds into one list
if isinstance(data, list):
    agents = data
else:
    agents = []
    for v in data.values():
        if isinstance(v, list):
            agents.extend(v)
for a in agents:
    if isinstance(a, dict) and a.get('name') == '$1':
        print(a.get('id',''))
        sys.exit(0)
" 2>/dev/null || echo ""
}

upsert_env() {
    local key="$1" val="$2"
    [ -z "$val" ] && { echo "  ✗ $key unresolved — paste the agent ID manually into .env"; return; }
    [ -f "$ENV_FILE" ] || { [ -f "$ENV_EXAMPLE" ] && cp "$ENV_EXAMPLE" "$ENV_FILE" || : > "$ENV_FILE"; }
    if grep -qE "^${key}=" "$ENV_FILE"; then
        sed -i.bak "s|^${key}=.*|${key}=${val}|" "$ENV_FILE" && rm -f "${ENV_FILE}.bak"
    else
        printf '\n%s=%s\n' "$key" "$val" >> "$ENV_FILE"
    fi
    echo "  ✓ $key=$val"
}

echo ""
echo "=== Resolving agent IDs ==="
upsert_env WO_SUPERVISOR_AGENT_ID "$(resolve_id supervisor_agent)"
upsert_env WO_TRIAGE_AGENT_ID     "$(resolve_id flight_triage_agent)"
echo "  ✗ WO_SLACK_AGENT_ID  — paste manually after docs/07-slack-setup.md"
echo "  ✗ WO_SNOW_AGENT_ID   — paste manually after docs/06-servicenow-setup.md (optional)"
echo "  ✗ WO_GMAIL_AGENT_ID  — paste manually after docs/08-gmail-setup.md (optional)"

echo ""
echo "=== Done ==="
"$ORCHESTRATE" agents list
echo ""
echo "✓ Gate Change Cascade environment bootstrapped."
echo "  WO_SUPERVISOR_AGENT_ID and WO_TRIAGE_AGENT_ID written to ${ENV_FILE}"
echo "  (Optional) Paste WO_SLACK_AGENT_ID after docs/07-slack-setup.md"
echo "  (Optional) Paste WO_SNOW_AGENT_ID after docs/06-servicenow-setup.md"
echo "  (Optional) Paste WO_GMAIL_AGENT_ID after docs/08-gmail-setup.md"
echo "  Then restart the demo: bash ${ROOT_DIR}/app-run-local.sh"
