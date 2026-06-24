#!/bin/bash
set -e

DOCKER_IMAGE=""
APP_NAME=""
CE_PROJECT=""
CE_RESOURCE_GROUP=""
CE_REGION=""

source "$(dirname "$0")/.env"

echo "==> Building image for linux/amd64..."
docker build --platform linux/amd64 -t "$DOCKER_IMAGE:latest" .

echo "==> Pushing to Docker Hub..."
docker push "$DOCKER_IMAGE:latest"

echo "==> Targeting IBM Cloud resource group and region..."
ibmcloud target -g "$CE_RESOURCE_GROUP" -r "$CE_REGION"

echo "==> Selecting Code Engine project..."
ibmcloud ce project select --name "$CE_PROJECT"

if ibmcloud ce app get --name "$APP_NAME" &>/dev/null; then
  echo "==> Updating existing app..."
  ibmcloud ce app update \
    --name "$APP_NAME" \
    --image "docker.io/$DOCKER_IMAGE:latest" \
    --port 8080 \
    --env CONFLUENT_BOOTSTRAP_SERVERS="$CONFLUENT_BOOTSTRAP_SERVERS" \
    --env CONFLUENT_API_KEY="$CONFLUENT_API_KEY" \
    --env CONFLUENT_API_SECRET="$CONFLUENT_API_SECRET"
else
  echo "==> Creating new app..."
  ibmcloud ce app create \
    --name "$APP_NAME" \
    --image "docker.io/$DOCKER_IMAGE:latest" \
    --port 8080 \
    --min-scale 1 \
    --env CONFLUENT_BOOTSTRAP_SERVERS="$CONFLUENT_BOOTSTRAP_SERVERS" \
    --env CONFLUENT_API_KEY="$CONFLUENT_API_KEY" \
    --env CONFLUENT_API_SECRET="$CONFLUENT_API_SECRET"
fi

echo "==> Waiting for app to be ready..."
until ibmcloud ce app get --name "$APP_NAME" 2>&1 | grep -q "Ready.*true"; do sleep 5; done

URL=$(ibmcloud ce app get --name "$APP_NAME" 2>&1 | grep "^URL:" | awk '{print $2}')
echo ""
echo "==> App live at: $URL"
echo "==> Health check:"
curl -s "$URL/health"
echo ""
