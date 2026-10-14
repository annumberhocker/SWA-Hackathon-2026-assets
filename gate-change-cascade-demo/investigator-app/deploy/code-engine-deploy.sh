#!/usr/bin/env bash
# code-engine-deploy.sh — Gate Change Cascade investigator-app
#
# Builds the investigator-app image locally with Podman (falls back to Docker),
# pushes it to IBM Cloud Container Registry (ICR), then deploys it as a Code
# Engine application with --min-scale 1 (always warm).
#
# The ICR registry hostname is derived automatically from REGION:
#   us-south  → us.icr.io
#   ca-tor    → ca.icr.io
#   eu-de     → de.icr.io
#   eu-gb     → uk.icr.io
#   au-syd    → au.icr.io
#   jp-tok    → jp.icr.io
#   (default) → us.icr.io
#
# Usage (from gate-change-cascade/):
#   bash investigator-app/deploy/code-engine-deploy.sh
#
# Prerequisites:
#   - Podman or Docker installed and running locally
#   - ibmcloud CLI with container-registry and code-engine plugins
#     (ibmcloud plugin install container-registry code-engine -r 'IBM Cloud')
#   - investigator-app/deploy/.env filled in (copy from .env.example)
#   - gate-change-cascade/.env with CONFLUENT_* / KAFKA_* vars populated
#
# To force a specific container runtime, set in investigator-app/deploy/.env:
#   DOCKER=podman   (or DOCKER=docker, or a full path)

set -euo pipefail

# ── Locate paths ──────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_ENV="${SCRIPT_DIR}/.env"
GCC_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"      # gate-change-cascade/
GCC_ENV="${GCC_ROOT}/.env"

# ── Load deploy .env ──────────────────────────────────────────────────────────
if [ ! -f "${DEPLOY_ENV}" ]; then
    echo "ERROR: ${DEPLOY_ENV} not found."
    echo "   Run: cp investigator-app/deploy/.env.example investigator-app/deploy/.env"
    exit 1
fi
set -a; source "${DEPLOY_ENV}"; set +a

# ── Load GCC .env for Confluent credentials ───────────────────────────────────
if [ -f "${GCC_ENV}" ]; then
    set -a; source "${GCC_ENV}"; set +a
fi

# ── Config ────────────────────────────────────────────────────────────────────
REGION="${REGION:-ca-tor}"
RESOURCE_GROUP="${RESOURCE_GROUP:?RESOURCE_GROUP must be set in deploy/.env}"
WO_API_KEY="${WO_API_KEY:?WO_API_KEY must be set in deploy/.env}"
ICR_NAMESPACE_DEFAULT="${ICR_NAMESPACE:-gcc-investigator}"   # fallback name if we must create one

CE_PROJECT_NAME="${CE_PROJECT_NAME:-ce-${RESOURCE_GROUP}}"
CE_APP_NAME="${CE_APP_NAME:-gcc-investigator}"
REGISTRY_SECRET_NAME="${REGISTRY_SECRET_NAME:-gcc-icr-secret}"

# ── Derive ICR hostname from region ───────────────────────────────────────────
# Maps IBM Cloud region → regional ICR push hostname.
# Uses the public endpoint (us.icr.io, ca.icr.io, …); Code Engine pulls via
# the private endpoint (private.us.icr.io …) automatically when the registry
# secret is created with the public hostname.
case "${REGION}" in
    us-south|us-east)   ICR_HOST="us.icr.io" ;;
    ca-tor)             ICR_HOST="ca.icr.io" ;;
    eu-de)              ICR_HOST="de.icr.io" ;;
    eu-gb)              ICR_HOST="uk.icr.io" ;;
    au-syd)             ICR_HOST="au.icr.io" ;;
    jp-tok|jp-osa)      ICR_HOST="jp.icr.io" ;;
    *)
        echo "WARN: unknown region '${REGION}' — defaulting ICR host to us.icr.io"
        ICR_HOST="us.icr.io"
        ;;
esac

# IMAGE_REF is set after the ICR namespace is resolved below.

# ── Detect container runtime ─ prefer podman, fall back to docker ─────────────
if [ -z "${DOCKER:-}" ]; then
    DOCKER="$(command -v podman 2>/dev/null || command -v docker 2>/dev/null || true)"
fi
if [ -z "${DOCKER}" ]; then
    echo "ERROR: podman or docker not found. Install one to build the image locally."
    exit 1
fi

# ── Banner ────────────────────────────────────────────────────────────────────
echo "╔════════════════════════════════════════════════════════════╗"
echo "║   IBM Code Engine — Gate Change Cascade Investigator API   ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "  Region:  ${REGION}"
echo "  Project: ${CE_PROJECT_NAME}"
echo ""

# ── IBM Cloud login ───────────────────────────────────────────────────────────
if ibmcloud target 2>/dev/null | grep -q "Not logged in"; then
    echo "Logging in to IBM Cloud..."
    ibmcloud login --apikey "${WO_API_KEY}" -r "${REGION}" -g "${RESOURCE_GROUP}" -q
    echo "✓ Logged in to IBM Cloud"
else
    ibmcloud target -r "${REGION}" -g "${RESOURCE_GROUP}" -q 2>/dev/null || \
        ibmcloud login --apikey "${WO_API_KEY}" -r "${REGION}" -g "${RESOURCE_GROUP}" -q
    echo "✓ Already logged in to IBM Cloud"
fi

# ── Resolve ICR namespace: search by resource group, create if none found ─────
# Note: ibmcloud cr commands do not support -q; suppress output with redirection.
echo "  Searching for container registry namespaces in resource group '${RESOURCE_GROUP}'..."
ibmcloud cr region-set "${REGION}" > /dev/null 2>&1 || true

# Resolve the resource group ID so we can match namespaces owned by it
RESOURCE_GROUP_ID="$(ibmcloud resource group "${RESOURCE_GROUP}" --output json 2>/dev/null | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['id'])" 2>/dev/null || \
    ibmcloud resource group "${RESOURCE_GROUP}" --output json 2>/dev/null | \
    grep -o '"id":"[^"]*"' | head -n1 | cut -d'"' -f4)"

# List all namespaces and pick the first one that belongs to this resource group
ICR_NAMESPACE="$(ibmcloud cr namespace-list -v --output json 2>/dev/null | \
    python3 -c "
import sys, json
nss = json.load(sys.stdin)
rg  = '${RESOURCE_GROUP_ID}'
matches = [n['name'] for n in nss if n.get('resource_group_id') == rg or n.get('resource_group') == rg]
print(matches[0] if matches else '')
" 2>/dev/null || true)"

if [[ -n "${ICR_NAMESPACE}" ]]; then
    echo "✓ Found existing ICR namespace: ${ICR_NAMESPACE}"
else
    ICR_NAMESPACE="${ICR_NAMESPACE_DEFAULT}"
    echo "  No existing ICR namespace found in resource group '${RESOURCE_GROUP}'."
    echo "  Creating ICR namespace '${ICR_NAMESPACE}'..."
    ibmcloud cr namespace-add -g "${RESOURCE_GROUP}" "${ICR_NAMESPACE}"
    echo "✓ ICR namespace created: ${ICR_NAMESPACE}"
fi

IMAGE_REF="${ICR_HOST}/${ICR_NAMESPACE}/gcc-investigator:latest"
echo "  Image:   ${IMAGE_REF}"

# ── Build image locally ───────────────────────────────────────────────────────
echo "  Building image locally (amd64 for Code Engine)…"
"${DOCKER}" build \
    --arch amd64 \
    -f "${SCRIPT_DIR}/api.Dockerfile" \
    -t "${IMAGE_REF}" \
    "${GCC_ROOT}"
echo "✓ Image built: ${IMAGE_REF}"

# ── Push to IBM Cloud Container Registry ─────────────────────────────────────
echo "  Logging in to ICR (${ICR_HOST})…"
ibmcloud cr login --client "$(basename "${DOCKER}")"
echo "  Pushing to ${ICR_HOST}…"
"${DOCKER}" push "${IMAGE_REF}"
echo "✓ Image pushed: ${IMAGE_REF}"

# ── Code Engine project ───────────────────────────────────────────────────────
if ! ibmcloud ce project list -q 2>/dev/null | grep -q "${CE_PROJECT_NAME}"; then
    echo "Creating Code Engine project ${CE_PROJECT_NAME}..."
    ibmcloud ce project create --name "${CE_PROJECT_NAME}" -q
fi
ibmcloud ce project select --name "${CE_PROJECT_NAME}" -q
echo "✓ Project selected"

# ── ICR registry secret ───────────────────────────────────────────────────────
# Code Engine uses the API key that is already authenticated to pull from ICR.
# The registry secret wraps the same API key used for ibmcloud login.
if ibmcloud ce registry list -q 2>/dev/null | grep -q "${REGISTRY_SECRET_NAME}"; then
    ibmcloud ce registry update \
        --name "${REGISTRY_SECRET_NAME}" \
        --server "${ICR_HOST}" \
        --username "iamapikey" \
        --password "${WO_API_KEY}" -q
else
    ibmcloud ce registry create \
        --name "${REGISTRY_SECRET_NAME}" \
        --server "${ICR_HOST}" \
        --username "iamapikey" \
        --password "${WO_API_KEY}" -q
fi
echo "✓ Registry secret ready"

# ── Deploy / update application ───────────────────────────────────────────────
echo "  Deploying to Code Engine…"

APP_ARGS=(
    --name "${CE_APP_NAME}"
    --image "${IMAGE_REF}"
    --registry-secret "${REGISTRY_SECRET_NAME}"
    --min-scale 1
    --max-scale 1
    --cpu 0.25
    --memory 0.5G
    --port 8080
    --env CONFLUENT_BOOTSTRAP_SERVERS="${CONFLUENT_BOOTSTRAP_SERVERS:-}"
    --env KAFKA_API_KEY="${KAFKA_API_KEY:-}"
    --env KAFKA_API_SECRET="${KAFKA_API_SECRET:-}"
)

if ibmcloud ce app list -q 2>/dev/null | grep -q "^${CE_APP_NAME}"; then
    echo "  Updating application..."
    ibmcloud ce app update "${APP_ARGS[@]}" --wait -q
else
    echo "  Creating application..."
    ibmcloud ce app create "${APP_ARGS[@]}" --wait -q
fi

# ── Retrieve public URL ───────────────────────────────────────────────────────
APP_URL="$(ibmcloud ce app get --name "${CE_APP_NAME}" --output json 2>/dev/null | \
    python3 -c "import sys,json; s=json.load(sys.stdin); print(s['status']['url'])" 2>/dev/null || \
    ibmcloud ce app get --name "${CE_APP_NAME}" 2>/dev/null | awk '/^URL/{print $2}')"

echo "  ✓ Application live"

# ── Write INVESTIGATOR_API_URL to both .env files ─────────────────────────────
for env_file in "${DEPLOY_ENV}" "${GCC_ENV}"; do
    if [ -f "${env_file}" ]; then
        if grep -q '^INVESTIGATOR_API_URL=' "${env_file}"; then
            sed -i.bak "s|^INVESTIGATOR_API_URL=.*|INVESTIGATOR_API_URL=${APP_URL}|" "${env_file}"
        else
            echo "INVESTIGATOR_API_URL=${APP_URL}" >> "${env_file}"
        fi
    fi
done

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                    Deployment Complete!                    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "┌─ ${CE_APP_NAME} ─────────────────────────────────────────┐"
echo "  URL:    ${APP_URL}"
echo "  Health: ${APP_URL}/healthz"
echo "  Docs:   ${APP_URL}/docs"
echo "└────────────────────────────────────────────────────────────┘"
echo ""
echo "INVESTIGATOR_API_URL written to:"
echo "  ${DEPLOY_ENV}"
echo "  ${GCC_ENV}"
echo ""
echo "Re-run bootstrap to bake the URL into the WXO tools:"
echo "  source .venv-orchestrate/bin/activate"
echo "  cd orchestrate && bash bootstrap_env.sh --reuse-env"
