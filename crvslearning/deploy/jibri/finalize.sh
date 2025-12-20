#!/usr/bin/env bash
# Finalize script invoked by Jibri after recording. It should publish the recording URL to the app webhook.
# This is a simple example; adapt to your storage and path layout.
set -euo pipefail

# Inputs (provided by jibri container environment)
#  - RECORDING_PATH: directory where files are stored (e.g., /config/recordings/<room-name>-<timestamp>)
#  - PUBLIC_BASE_URL: base URL where recordings are exposed (map your storage)
#  - WEBHOOK_URL: your backend endpoint (e.g., https://host/classrooms/recording/webhook/)
#  - WEBHOOK_TOKEN: secret header expected by backend
# Optional: try to extract session_id from room naming convention: CRVS_<JOINCODE>_<SESSIONID>

RECORDING_PATH=${RECORDING_PATH:-/config/recordings}
PUBLIC_BASE_URL=${PUBLIC_BASE_URL:-""}
WEBHOOK_URL=${WEBHOOK_URL:-""}
TOKEN=${WEBHOOK_TOKEN:-""}

if [[ -z "$WEBHOOK_URL" ]]; then
  echo "WEBHOOK_URL not set, skipping webhook call" >&2
  exit 0
fi

# Find last mp4 produced
FILE=$(find "$RECORDING_PATH" -type f -name '*.mp4' | sort | tail -n 1)
if [[ -z "${FILE}" ]]; then
  echo "No mp4 found in $RECORDING_PATH" >&2
  exit 0
fi

# Build a public URL; if using nginx to serve /recordings, set PUBLIC_BASE_URL accordingly
BASENAME=$(basename "$FILE")
if [[ -n "$PUBLIC_BASE_URL" ]]; then
  RECORDING_URL="${PUBLIC_BASE_URL%/}/$BASENAME"
else
  # Fallback to file path; backend may ignore if not HTTP
  RECORDING_URL="file://$FILE"
fi

# Try to extract session_id from filename pattern ..._<SESSIONID>.mp4
SESSION_ID=
if [[ "$BASENAME" =~ _([0-9]+)\.mp4$ ]]; then
  SESSION_ID="${BASH_REMATCH[1]}"
fi

if [[ -z "$SESSION_ID" ]]; then
  echo "SESSION_ID not found from filename; set SESSION_ID env to force" >&2
  SESSION_ID=${SESSION_ID:-}
fi

# Post to webhook if we have both fields
if [[ -n "$SESSION_ID" ]]; then
  echo "Posting recording to webhook: session_id=$SESSION_ID url=$RECORDING_URL"
  curl -sS -X POST "$WEBHOOK_URL" \
    -H 'Content-Type: application/json' \
    ${TOKEN:+-H "X-Webhook-Token: $TOKEN"} \
    -d "{ \"session_id\": $SESSION_ID, \"recording_url\": \"$RECORDING_URL\" }" || true
else
  echo "Skipping webhook POST (missing session_id)" >&2
fi
