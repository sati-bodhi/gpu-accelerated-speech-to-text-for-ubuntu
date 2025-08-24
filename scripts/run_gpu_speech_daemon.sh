#!/bin/bash
# Client script for persistent speech daemon

AUDIO_FILE="$1"
REQUEST_DIR="/tmp/speech_requests"
RESPONSE_DIR="/tmp/speech_responses"
STATUS_FILE="/tmp/speech_daemon_status.json"

# Check if daemon is running
if [ ! -f "$STATUS_FILE" ]; then
    echo "Starting persistent speech daemon..."
    cd "/home/sati/speech-to-text-for-ubuntu"
    nohup ./venv/bin/python3 src/speech_daemon_optimized.py > /tmp/speech_daemon_startup.log 2>&1 &
    
    # Wait for daemon to start
    sleep 3
    
    if [ ! -f "$STATUS_FILE" ]; then
        echo "Failed to start daemon"
        exit 1
    fi
fi

# Check daemon status
if ! python3 -c "
import json, time
try:
    with open('$STATUS_FILE') as f:
        status = json.load(f)
    if not status.get('ready', False):
        exit(1)
    if time.time() - status.get('timestamp', 0) > 30:
        exit(1)  # Daemon seems stale
except:
    exit(1)
"; then
    echo "Daemon not ready, please check /tmp/speech_daemon.log"
    exit 1
fi

# Generate unique request ID
REQUEST_ID=$(date +%s%N)

# Create request
REQUEST_FILE="$REQUEST_DIR/${REQUEST_ID}.json"
mkdir -p "$REQUEST_DIR" "$RESPONSE_DIR"

python3 -c "
import json
request = {
    'id': '$REQUEST_ID',
    'audio_file': '$AUDIO_FILE',
    'timestamp': $(date +%s.%N)
}
with open('$REQUEST_FILE', 'w') as f:
    json.dump(request, f)
"

echo "Request sent to persistent daemon (zero model loading time)"

# Wait for response (with timeout)
RESPONSE_FILE="$RESPONSE_DIR/${REQUEST_ID}.json"
TIMEOUT=10
ELAPSED=0

while [ $ELAPSED -lt $TIMEOUT ]; do
    if [ -f "$RESPONSE_FILE" ]; then
        echo "Response received in ${ELAPSED}s (persistent model benefit!)"
        rm -f "$RESPONSE_FILE"
        exit 0
    fi
    sleep 0.1
    ELAPSED=$((ELAPSED + 1))
done

echo "Request timeout after ${TIMEOUT}s"
exit 1