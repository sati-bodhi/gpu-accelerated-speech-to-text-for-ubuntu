#!/bin/bash
# Smart session-based speech client with auto-startup

AUDIO_FILE="$1"
REQUEST_DIR="/tmp/speech_session_requests" 
RESPONSE_DIR="/tmp/speech_session_responses"
STATUS_FILE="/tmp/session_daemon_status.json"
SESSION_FILE="/tmp/session_daemon_active"
PROJECT_DIR="/home/sati/speech-to-text-for-ubuntu"

# Function to start session daemon
start_session_daemon() {
    echo "Starting session speech daemon..."
    cd "$PROJECT_DIR"
    
    # Don't kill existing daemon - let it run for session persistence
    # Only start if no daemon is running
    if pgrep -f "session_daemon.py" > /dev/null; then
        echo "Found existing daemon process, checking status..."
        return 0  # Let status check handle it
    fi
    
    # Start new session daemon (10 minute timeout)
    nohup ./venv/bin/python3 src/session_daemon.py 600 > /tmp/session_daemon_startup.log 2>&1 &
    
    # Wait for daemon to start
    for i in {1..30}; do
        if [ -f "$STATUS_FILE" ] && [ -f "$SESSION_FILE" ]; then
            echo "Session daemon started successfully"
            return 0
        fi
        sleep 0.1
    done
    
    echo "Failed to start session daemon"
    return 1
}

# Function to check daemon status
check_daemon_status() {
    # Check if status file exists and is recent
    if [ ! -f "$STATUS_FILE" ]; then
        return 1
    fi
    
    # Check if daemon is responsive using Python
    python3 -c "
import json, time, sys
try:
    with open('$STATUS_FILE') as f:
        status = json.load(f)
    
    # Check if daemon is active and responsive (within 60s)
    if not status.get('active', False):
        sys.exit(1)
    
    timestamp = status.get('timestamp', 0)
    if time.time() - timestamp > 300:  # 5 minutes tolerance
        sys.exit(1)  # Daemon seems stale
        
    print(f'Daemon status: model_loaded={status.get(\"model_loaded\", False)}, device={status.get(\"device\", \"unknown\")}')
    
except Exception as e:
    sys.exit(1)
"
}

# Main logic
echo "=== Hybrid Session Speech Client ==="

# Check if daemon is running and responsive
if ! check_daemon_status; then
    echo "Session daemon not found or unresponsive"
    
    if ! start_session_daemon; then
        echo "Failed to start daemon, check /tmp/session_daemon.log"
        exit 1
    fi
    
    # Wait a bit more for full initialization
    sleep 1
    
    if ! check_daemon_status; then
        echo "Daemon started but not responding properly"
        exit 1
    fi
else
    echo "Using existing session daemon"
fi

# Generate unique request ID
REQUEST_ID=$(date +%s%N)
REQUEST_FILE="$REQUEST_DIR/${REQUEST_ID}.json"
RESPONSE_FILE="$RESPONSE_DIR/${REQUEST_ID}.json"

# Create directories
mkdir -p "$REQUEST_DIR" "$RESPONSE_DIR"

# Create request
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

echo "Request sent to session daemon..."

# Wait for response with timeout
TIMEOUT=15
ELAPSED=0

while [ $ELAPSED -lt $TIMEOUT ]; do
    if [ -f "$RESPONSE_FILE" ]; then
        # Check response content
        RESPONSE_INFO=$(python3 -c "
import json
try:
    with open('$RESPONSE_FILE') as f:
        resp = json.load(f)
    
    session_active = resp.get('session_active', False)
    device = resp.get('device', 'unknown')
    results = resp.get('results', [])
    
    print(f'Response received: session_active={session_active}, device={device}, results={len(results)}')
except:
    print('Response parsing failed')
")
        
        echo "$RESPONSE_INFO"
        echo "Session processing completed in ${ELAPSED}s"
        
        rm -f "$RESPONSE_FILE"
        exit 0
    fi
    
    sleep 0.1
    ELAPSED=$((ELAPSED + 1))
done

echo "Request timeout after ${TIMEOUT}s"
echo "Check daemon status: cat $STATUS_FILE"
exit 1