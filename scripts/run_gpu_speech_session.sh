#!/bin/bash
# Smart session-based speech client with auto-startup

AUDIO_FILE="$1"
REQUEST_DIR="/tmp/speech_session_requests" 
RESPONSE_DIR="/tmp/speech_session_responses"
STATUS_FILE="/tmp/session_daemon_status.json"
SESSION_FILE="/tmp/session_daemon_active"
PROJECT_DIR="/home/sati/speech-to-text-for-ubuntu"

# Function to check if daemon is already running using PID file
check_daemon_pid() {
    local pid_file="/tmp/session_daemon.pid"
    
    # Check if PID file exists
    if [ ! -f "$pid_file" ]; then
        return 1  # No PID file, daemon not running
    fi
    
    # Check if process is actually running
    local pid=$(cat "$pid_file" 2>/dev/null)
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        echo "Found running daemon with PID $pid"
        return 0  # Daemon is running
    else
        # PID file exists but process not running - clean up
        rm -f "$pid_file"
        return 1  # Daemon not running
    fi
}

# Function to start session daemon with atomic locking
start_session_daemon() {
    echo "Starting session speech daemon..."
    cd "$PROJECT_DIR"
    
    local lock_file="/tmp/session_daemon_startup.lock"
    
    # Atomic startup with file locking to prevent race conditions
    (
        # Try to acquire exclusive lock (wait up to 5 seconds)
        if ! flock -x -w 5 200; then
            echo "Could not acquire startup lock, another daemon may be starting"
            exit 1
        fi
        
        # Double-check if daemon started while we were waiting for lock
        if check_daemon_pid; then
            echo "Session daemon already running (started while waiting for lock)"
            exit 0
        fi
        
        echo "Acquired startup lock, proceeding with daemon startup..."
        
        # Clean up any stale files before starting
        rm -f /tmp/session_daemon.pid /tmp/session_daemon_status.json /tmp/session_daemon_active
        
        # Set CUDNN library paths before starting daemon
        export LD_LIBRARY_PATH="$PROJECT_DIR/venv/lib/python3.10/site-packages/nvidia/cudnn/lib:$PROJECT_DIR/venv/lib/python3.10/site-packages/nvidia/cublas/lib:$LD_LIBRARY_PATH"
        
        # Start new session daemon (10 minute timeout)
        nohup ./venv/bin/python3 src/session_daemon.py 600 > /tmp/session_daemon_startup.log 2>&1 &
        
        # Wait for daemon to start and create files
        for i in {1..30}; do
            if [ -f "/tmp/session_daemon.pid" ] && [ -f "$STATUS_FILE" ]; then
                echo "Session daemon started successfully"
                exit 0
            fi
            sleep 0.1
        done
        
        echo "Failed to start session daemon"
        exit 1
        
    ) 200>"$lock_file"
    
    # Return the exit code from the subshell
    return $?
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