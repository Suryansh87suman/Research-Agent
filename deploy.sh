#!/usr/bin/env bash
# deploy.sh — Build, push, and deploy to IBM Code Engine
# Usage: bash deploy.sh
#
# Prerequisites:
#   - ibmcloud CLI installed: https://cloud.ibm.com/docs/cli
#   - ibmcloud ce plugin:  ibmcloud plugin install code-engine
#   - ibmcloud cr plugin:  ibmcloud plugin install container-registry
#   - Docker Desktop running
#   - Logged in:  ibmcloud login --apikey YOUR_API_KEY -r us-south
#
# Set these variables before running:

REGISTRY="icr.io"                          # IBM Container Registry
NAMESPACE="your-icr-namespace"             # ibmcloud cr namespace-list
IMAGE_NAME="research-agent"
IMAGE_TAG="latest"
CE_PROJECT="research-agent-project"        # ibmcloud ce project list
CE_APP="research-agent"
REGION="us-south"

IMAGE="${REGISTRY}/${NAMESPACE}/${IMAGE_NAME}:${IMAGE_TAG}"

set -euo pipefail

echo ""
echo "======================================================"
echo "  IBM Research Agent — Code Engine Deployment"
echo "======================================================"

# 1. Log in to IBM Container Registry
echo ""
echo ">>> Step 1/5  Logging in to IBM Container Registry…"
ibmcloud cr login

# 2. Build the Docker image
echo ""
echo ">>> Step 2/5  Building Docker image: ${IMAGE}"
docker build -t "${IMAGE}" .

# 3. Push to IBM Container Registry
echo ""
echo ">>> Step 3/5  Pushing image to IBM Container Registry…"
docker push "${IMAGE}"

# 4. Target the Code Engine project
echo ""
echo ">>> Step 4/5  Targeting Code Engine project: ${CE_PROJECT}"
ibmcloud ce project select --name "${CE_PROJECT}" 2>/dev/null || \
  ibmcloud ce project create --name "${CE_PROJECT}"

# 5a. Create secrets (only on first deploy — skip if already exist)
echo ""
echo ">>> Step 5a/5 Creating Code Engine secrets…"
ibmcloud ce secret create \
  --name research-agent-secrets \
  --from-literal IBM_WATSONX_API_KEY="${IBM_WATSONX_API_KEY:-REPLACE_ME}" \
  --from-literal IBM_WATSONX_PROJECT_ID="${IBM_WATSONX_PROJECT_ID:-REPLACE_ME}" \
  --from-literal SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')" \
  2>/dev/null || echo "  Secrets already exist — skipping."

# 5b. Deploy or update the application
echo ""
echo ">>> Step 5b/5 Deploying application to IBM Code Engine…"
if ibmcloud ce application get --name "${CE_APP}" &>/dev/null; then
  echo "  Application exists — updating image…"
  ibmcloud ce application update \
    --name "${CE_APP}" \
    --image "${IMAGE}"
else
  echo "  Creating new application…"
  ibmcloud ce application create \
    --name "${CE_APP}" \
    --image "${IMAGE}" \
    --registry-secret ce-icr-secret \
    --port 8080 \
    --cpu 0.5 \
    --memory 2G \
    --min-scale 0 \
    --max-scale 5 \
    --env IBM_WATSONX_URL="https://us-south.ml.cloud.ibm.com" \
    --env GRANITE_MODEL_ID="meta-llama/llama-3-3-70b-instruct" \
    --env GRANITE_MAX_TOKENS="1024" \
    --env GRANITE_TEMPERATURE="0.7" \
    --env MAX_PAPERS_PER_QUERY="10" \
    --env OUTPUT_DIR="/tmp/outputs" \
    --env LOG_LEVEL="INFO" \
    --env PORT="8080" \
    --env-from-secret research-agent-secrets \
    --wait
fi

# 6. Print the live URL
echo ""
echo "======================================================"
URL=$(ibmcloud ce application get --name "${CE_APP}" --output json 2>/dev/null \
      | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',{}).get('url',''))" 2>/dev/null || true)
if [ -n "${URL}" ]; then
  echo "  ✅  Application live at: ${URL}"
else
  echo "  Run:  ibmcloud ce application get --name ${CE_APP}"
fi
echo "======================================================"
echo ""
