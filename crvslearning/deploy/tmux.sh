#!/usr/bin/env bash
# Launch a tmux session tailored for CRVS one-host dev environment
# Panes:
#  - Pane 1: run onehost-dev stack
#  - Pane 2: nginx logs
#  - Pane 3: web logs
#  - Pane 4: jibri logs (if present)

set -euo pipefail

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux is not installed. Please install tmux to use this script." >&2
  exit 1
fi

SESSION_NAME=${SESSION_NAME:-crvs}

# Determine terminal size
set -- $(stty size || echo "40 120") # $1=rows, $2=columns
ROWS=${1}
COLS=${2}

# Start a new tmux session in detached mode with resizable panes
# Main window sized to terminal minus 1 row
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
  tmux kill-session -t "$SESSION_NAME" || true
fi

tmux new-session -s "$SESSION_NAME" -n "$SESSION_NAME" -d -x "$COLS" -y "$((ROWS - 1))"
TMUX_STARTED=1

# Pane 1: bring up the stack (dev flavor)
tmux send-keys -t "$SESSION_NAME" "./deploy/deploy.sh onehost-dev" C-m

# Split horizontally: Pane 2 right (30%) for nginx logs
tmux split-window -t "$SESSION_NAME" -h -l '30%'
tmux send-keys -t "$SESSION_NAME":0.1 "docker compose logs -f nginx" C-m

# Select left pane and split vertically: Pane 3 bottom for web logs
tmux select-pane -t "$SESSION_NAME":0.0
 tmux split-window -t "$SESSION_NAME" -v
 tmux send-keys -t "$SESSION_NAME":0.2 "docker compose logs -f web" C-m

# Select bottom-left pane and split vertically again for jibri logs if available
 tmux split-window -t "$SESSION_NAME" -v
 tmux send-keys -t "$SESSION_NAME":0.3 "docker compose -f docker-compose.jitsi.yml logs -f jibri" C-m

# Enable mouse and attach
 tmux setw -g mouse on
 tmux attach -t "$SESSION_NAME"
