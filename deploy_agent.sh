#!/bin/bash
set -e

WXO_ENV=""
WXO_URL=""

source "$(dirname "$0")/.env"

VENV_ORCHESTRATE="$(dirname "$0")/.venv/bin/orchestrate"

echo "==> Adding/activating WatsonX Orchestrate environment..."
"$VENV_ORCHESTRATE" env add --name "$WXO_ENV" --url "$WXO_URL" --activate 2>/dev/null || \
  "$VENV_ORCHESTRATE" env activate "$WXO_ENV"

echo "==> Importing OpenAPI tools..."
"$VENV_ORCHESTRATE" tools import -k openapi -f agent/openapi.yaml

echo "==> Importing agent..."
"$VENV_ORCHESTRATE" agents import -f agent/race_strategist.yaml

echo "==> Deploying agent..."
"$VENV_ORCHESTRATE" agents deploy -n race_strategist

echo ""
echo "==> Done. race_strategist is live on $WXO_ENV."
