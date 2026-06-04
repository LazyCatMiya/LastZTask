#!/usr/bin/env bash
set -euo pipefail

MANIFEST_TEMPLATE="${MANIFEST_TEMPLATE:-k8s/cronjob.yaml}"
PLATFORM="${PLATFORM:-linux/amd64}"

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required environment variable: $name" >&2
    exit 2
  fi
}

require_env GCLOUD_ACCOUNT
require_env PROJECT_ID
require_env CLUSTER_NAME
require_env CLUSTER_ZONE
require_env IMAGE

cd "$(dirname "$0")/.."

RENDERED_MANIFEST="$(mktemp)"
trap 'rm -f "$RENDERED_MANIFEST"' EXIT

echo "Using gcloud account: $GCLOUD_ACCOUNT"
gcloud config set account "$GCLOUD_ACCOUNT"
gcloud config set project "$PROJECT_ID"

echo "Configuring Docker auth for Artifact Registry"
gcloud auth configure-docker asia-docker.pkg.dev --quiet

echo "Getting GKE credentials: $CLUSTER_NAME ($CLUSTER_ZONE)"
gcloud container clusters get-credentials "$CLUSTER_NAME" \
  --zone "$CLUSTER_ZONE" \
  --project "$PROJECT_ID"

echo "Building image: $IMAGE ($PLATFORM)"
docker build --platform "$PLATFORM" -t "$IMAGE" .

echo "Pushing image: $IMAGE"
docker push "$IMAGE"

echo "Rendering Kubernetes manifest: $MANIFEST_TEMPLATE"
sed "s#__IMAGE__#$IMAGE#g" "$MANIFEST_TEMPLATE" > "$RENDERED_MANIFEST"

echo "Applying Kubernetes manifest"
kubectl apply -f "$RENDERED_MANIFEST"

echo "Done."
