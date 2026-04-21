#!/usr/bin/env bash
# Idempotent Databricks workspace provisioning for ADF_DataCycleProject.
#
# Required environment variables:
#   DATABRICKS_HOST           - https URL of the workspace (e.g. https://adb-123.azuredatabricks.net)
#   DATABRICKS_TOKEN          - PAT with workspace-admin rights
#   ENVIRONMENT               - dev | prod
#   GITHUB_ACCOUNT            - GitHub org/user owning ADF_DataCycleProject (for Repos)
#   DATABRICKS_USER           - email of the Databricks user under whose Repos path to clone
#                               (e.g. dylan.sanderso@hes-so.ch — must match the path referenced
#                               by ADF DatabricksNotebook activities)
#   KV_RESOURCE_ID            - ARM resource ID of the Key Vault backing the secret scope
#   KV_URI                    - Key Vault DNS URI (e.g. https://kv-datacycle-dev.vault.azure.net/)
#
# Outputs the chosen cluster_id to /tmp/databricks_cluster_id.txt for downstream steps.

set -euo pipefail

: "${DATABRICKS_HOST:?Missing DATABRICKS_HOST}"
: "${DATABRICKS_TOKEN:?Missing DATABRICKS_TOKEN}"
: "${ENVIRONMENT:?Missing ENVIRONMENT}"
: "${GITHUB_ACCOUNT:?Missing GITHUB_ACCOUNT}"
: "${DATABRICKS_USER:?Missing DATABRICKS_USER}"
: "${KV_RESOURCE_ID:?Missing KV_RESOURCE_ID}"
: "${KV_URI:?Missing KV_URI}"

export DATABRICKS_HOST DATABRICKS_TOKEN

CLUSTER_NAME="datacycle-cluster-${ENVIRONMENT}"
SCOPE_NAME="keyvault-scope"
REPO_PROVIDER="gitHub"
REPO_URL="https://github.com/${GITHUB_ACCOUNT}/ADF_DataCycleProject"
REPO_PATH="/Repos/${DATABRICKS_USER}/ADF_DataCycleProject"

echo "==> Databricks host: ${DATABRICKS_HOST}"

# ---- 1. Secret scope backed by Key Vault --------------------------------------------
echo "==> Ensuring secret scope '${SCOPE_NAME}' exists"
if databricks secrets list-scopes --output JSON 2>/dev/null \
    | python3 -c "import json,sys; d=json.load(sys.stdin); \
                   sys.exit(0 if any(s.get('name')=='${SCOPE_NAME}' for s in d.get('scopes',[])) else 1)"; then
  echo "    scope already present — skipping"
else
  databricks secrets create-scope "${SCOPE_NAME}" \
    --scope-backend-type AZURE_KEYVAULT \
    --backend-azure-keyvault "resource_id=${KV_RESOURCE_ID},dns_name=${KV_URI}"
  echo "    scope created"
fi

# ---- 2. Cluster ---------------------------------------------------------------------
echo "==> Ensuring cluster '${CLUSTER_NAME}' exists"
CLUSTER_ID=$(databricks clusters list --output JSON \
  | python3 -c "import json,sys,os; n=os.environ['CLUSTER_NAME']; \
                data=json.load(sys.stdin); \
                m=[c for c in data if c.get('cluster_name')==n]; \
                print(m[0]['cluster_id']) if m else print('')" CLUSTER_NAME="${CLUSTER_NAME}" || true)

if [[ -z "${CLUSTER_ID}" ]]; then
  echo "    creating new cluster"
  CLUSTER_SPEC=$(cat <<EOF
{
  "cluster_name": "${CLUSTER_NAME}",
  "spark_version": "13.3.x-scala2.12",
  "node_type_id": "Standard_DS3_v2",
  "autotermination_minutes": 30,
  "num_workers": 1,
  "spark_conf": {
    "spark.databricks.delta.preview.enabled": "true"
  }
}
EOF
)
  CLUSTER_ID=$(databricks clusters create --json "${CLUSTER_SPEC}" \
    | python3 -c "import json,sys; print(json.load(sys.stdin)['cluster_id'])")
  echo "    created cluster_id=${CLUSTER_ID}"
else
  echo "    cluster already exists cluster_id=${CLUSTER_ID}"
fi

# ---- 3. Git Repo --------------------------------------------------------------------
echo "==> Ensuring Repo '${REPO_PATH}' exists"
EXISTING_REPO_ID=$(databricks repos list --output JSON \
  | python3 -c "import json,sys,os; p=os.environ['REPO_PATH']; \
                data=json.load(sys.stdin); \
                m=[r for r in data.get('repos',[]) if r.get('path')==p]; \
                print(m[0]['id']) if m else print('')" REPO_PATH="${REPO_PATH}" || true)

if [[ -z "${EXISTING_REPO_ID}" ]]; then
  echo "    creating repo at ${REPO_PATH}"
  databricks repos create "${REPO_URL}" "${REPO_PROVIDER}" --path "${REPO_PATH}"
else
  echo "    repo already exists id=${EXISTING_REPO_ID} — pulling latest"
  databricks repos update "${EXISTING_REPO_ID}" --branch main
fi

# ---- 4. Emit cluster ID for downstream steps ----------------------------------------
echo "${CLUSTER_ID}" > /tmp/databricks_cluster_id.txt
echo "==> Wrote cluster_id to /tmp/databricks_cluster_id.txt: ${CLUSTER_ID}"
