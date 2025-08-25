# Session API Reference

## Overview

The hybrid session system uses file-based Inter-Process Communication (IPC) with JSON payloads for reliable, high-performance transcription requests. This document provides complete API specifications for developers integrating with the session daemon.

## File System Locations

### Core Directories

```bash
/tmp/speech_session_requests/     # Incoming transcription requests
/tmp/speech_session_responses/    # Daemon responses with results  
/tmp/session_daemon_status.json   # Real-time daemon status
/tmp/session_daemon_active        # Session marker file
/tmp/session_daemon.log           # Processing logs
/tmp/key_listener.log             # Client activity logs
```

### File Naming Convention

**Request Files**: `{timestamp_microseconds}.json`
**Response Files**: `{timestamp_microseconds}.json` (matching request ID)
**Audio Files**: `/tmp/recorded_audio_{timestamp_microseconds}.wav`

Example: `1756080306440117328.json`

## Request API

### Creating a Request

**1. Generate Unique Request ID**
```bash
REQUEST_ID=$(date +%s%N)  # Timestamp with nanosecond precision
```

**2. Create Request File**
```bash
REQUEST_FILE="/tmp/speech_session_requests/${REQUEST_ID}.json"
```

**3. Request JSON Structure**
```json
{
    "id": "1756080306440117328",
    "audio_file": "/tmp/recorded_audio_1756080302547.wav",
    "timestamp": 1756080306.440
}
```

### Request Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique identifier (timestamp recommended) |
| `audio_file` | string | Yes | Absolute path to WAV audio file |
| `timestamp` | number | Yes | Request creation time (Unix timestamp) |

### Audio File Requirements

**Format**: WAV (RIFF header)
**Sample Rate**: 16000 Hz recommended (auto-converted if different)
**Channels**: Mono preferred (stereo auto-converted)
**Bit Depth**: 16-bit PCM
**Duration**: No strict limits (very short audio <150ms may be filtered)

**Supported Formats**:
- WAV (recommended)
- FLAC, MP3, M4A (auto-converted by faster-whisper)

## Response API

### Response Structure

```json
{
    "id": "1756080306440117328",
    "results": [
        "This is the first transcribed segment",
        "This is the second segment if multiple were found"
    ],
    "timestamp": 1756080307.017,
    "device": "cuda",
    "session_active": true
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Matching request identifier |
| `results` | array | Array of transcribed text segments |
| `timestamp` | number | Response completion time |
| `device` | string | Processing device: "cuda" or "cpu" |
| `session_active` | boolean | True if model is cached in session |

### Response Timing

**File Creation**: Response file appears when processing is complete
**Timeout**: Client should timeout after 15-30 seconds
**Cleanup**: Response files should be deleted after reading

## Status API

### Daemon Status

**File**: `/tmp/session_daemon_status.json`

```json
{
    "active": true,
    "model_loaded": true,
    "device": "cuda",
    "model_size": "large-v3",
    "processing": false,
    "last_activity": 1756080307.017,
    "session_timeout": 600,
    "timestamp": 1756080307.018,
    "pid": 172849
}
```

### Status Fields

| Field | Type | Description |
|-------|------|-------------|
| `active` | boolean | Daemon running and responsive |
| `model_loaded` | boolean | Whisper model cached in GPU memory |
| `device` | string | Processing device: "cuda" or "cpu" |
| `model_size` | string | Loaded model: "large-v3", "medium", etc. |
| `processing` | boolean | Currently handling a request |
| `last_activity` | number | Timestamp of last processed request |
| `session_timeout` | number | Inactivity timeout in seconds (default: 600) |
| `timestamp` | number | Status file update time |
| `pid` | number | Daemon process ID |

### Session Marker

**File**: `/tmp/session_daemon_active`

```json
{
    "started": 1756080009.563,
    "pid": 172849
}
```

Indicates daemon is running. File is removed on clean shutdown.

## Client Implementation

### Basic Client Example

```bash
#!/bin/bash
# Simple session client example

AUDIO_FILE="$1"
REQUEST_ID=$(date +%s%N)
REQUEST_FILE="/tmp/speech_session_requests/${REQUEST_ID}.json"
RESPONSE_FILE="/tmp/speech_session_responses/${REQUEST_ID}.json"

# Create request
cat > "$REQUEST_FILE" << EOF
{
    "id": "$REQUEST_ID",
    "audio_file": "$AUDIO_FILE", 
    "timestamp": $(date +%s.%N)
}
EOF

# Wait for response (with timeout)
TIMEOUT=15
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
    if [ -f "$RESPONSE_FILE" ]; then
        # Process response
        cat "$RESPONSE_FILE"
        rm -f "$RESPONSE_FILE"
        exit 0
    fi
    sleep 0.1
    ELAPSED=$((ELAPSED + 1))
done

echo "Request timeout after ${TIMEOUT}s"
exit 1
```

### Python Client Example

```python
import json
import time
import os
from pathlib import Path

def transcribe_audio(audio_file):
    """Send transcription request to session daemon"""
    
    # Generate request
    request_id = str(int(time.time() * 1_000_000_000))  # Nanosecond timestamp
    request_file = Path(f"/tmp/speech_session_requests/{request_id}.json")
    response_file = Path(f"/tmp/speech_session_responses/{request_id}.json")
    
    # Create request
    request = {
        "id": request_id,
        "audio_file": str(audio_file),
        "timestamp": time.time()
    }
    
    with open(request_file, 'w') as f:
        json.dump(request, f)
    
    # Wait for response
    timeout = 15
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if response_file.exists():
            with open(response_file, 'r') as f:
                response = json.load(f)
            
            # Cleanup
            response_file.unlink()
            
            return response['results']
        
        time.sleep(0.1)
    
    raise TimeoutError(f"No response after {timeout}s")

# Usage
try:
    results = transcribe_audio("/path/to/audio.wav")
    print("Transcription:", " ".join(results))
except TimeoutError as e:
    print(f"Error: {e}")
```

## Error Handling

### Common Error Scenarios

**1. Daemon Not Running**
- **Symptom**: No response file appears
- **Check**: `ls /tmp/session_daemon_active`
- **Solution**: Start daemon or use auto-start client

**2. Request Timeout**
- **Symptom**: No response after 15+ seconds
- **Check**: `cat /tmp/session_daemon_status.json`
- **Solution**: Restart daemon, check CUDNN libraries

**3. Audio File Issues**
- **Symptom**: Empty results array in response
- **Check**: File exists, proper format, contains audio
- **Solution**: Verify audio file and duration

**4. CUDNN Library Errors**
- **Symptom**: Daemon crashes after few requests
- **Check**: `/tmp/session_daemon.log` for library errors
- **Solution**: Set LD_LIBRARY_PATH before daemon startup

### Error Response Format

```json
{
    "id": "1756080306440117328",
    "results": [],
    "timestamp": 1756080307.017,
    "device": "cuda",
    "session_active": false,
    "error": "Audio file not found: /tmp/missing_file.wav"
}
```

## Performance Characteristics

### Request Processing Times

| Scenario | Processing Time | Notes |
|----------|----------------|--------|
| **First Request (Cold)** | 1.5-2.0s | Includes model loading |
| **Subsequent (Cached)** | 0.3-0.5s | Session model cached |
| **Empty Audio (Filtered)** | 0.02-0.05s | Pre-filtered, no GPU |
| **CPU Fallback** | 8-12s | Automatic if GPU unavailable |

### Session Behavior

- **Session Duration**: 10 minutes of inactivity (configurable)
- **Session Extension**: Each request extends timeout
- **Memory Usage**: 3GB VRAM during active session
- **Startup Time**: ~0.5s daemon initialization

### File I/O Performance

- **Request Creation**: < 1ms
- **Response Reading**: < 1ms  
- **File Cleanup**: Automatic after response reading
- **Concurrent Requests**: Processed sequentially by daemon

## Daemon Management

### Starting Session Daemon

```bash
# Manual start (10 minute timeout)
./venv/bin/python3 src/session_daemon.py 600 &

# Custom timeout (30 minutes)
./venv/bin/python3 src/session_daemon.py 1800 &

# With proper CUDNN paths
export LD_LIBRARY_PATH="./venv/lib/python3.10/site-packages/nvidia/cudnn/lib:./venv/lib/python3.10/site-packages/nvidia/cublas/lib:$LD_LIBRARY_PATH"
./venv/bin/python3 src/session_daemon.py 600 &
```

### Monitoring Daemon

```bash
# Check if running
pgrep -f session_daemon.py

# View status
cat /tmp/session_daemon_status.json | jq

# Monitor real-time logs
tail -f /tmp/session_daemon.log

# Check processing performance
grep "SESSION transcription" /tmp/session_daemon.log | tail -10
```

### Stopping Daemon

```bash
# Graceful shutdown
pkill -f session_daemon.py

# Force kill (not recommended)
pkill -9 -f session_daemon.py

# Check cleanup
ls /tmp/session_daemon_*
ls /tmp/speech_session_*
```

## Integration Examples

### Shell Script Integration

```bash
#!/bin/bash
# Record and transcribe workflow

echo "Hold ENTER to record..."
read -r

echo "Recording... (Ctrl+C to stop)"
arecord -f S16_LE -r 16000 -c 1 /tmp/recording.wav

echo "Processing with session daemon..."
./scripts/run_gpu_speech_session.sh /tmp/recording.wav

echo "Done!"
```

### systemd Service

```ini
[Unit]
Description=Speech-to-Text Session Daemon
After=network.target

[Service]
Type=forking
User=your-username
Environment=LD_LIBRARY_PATH=/path/to/venv/lib/python3.10/site-packages/nvidia/cudnn/lib:/path/to/venv/lib/python3.10/site-packages/nvidia/cublas/lib
ExecStart=/path/to/venv/bin/python3 /path/to/src/session_daemon.py 600
PIDFile=/tmp/session_daemon.pid
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

### Web API Wrapper

```python
from flask import Flask, request, jsonify
import tempfile
import os

app = Flask(__name__)

@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file'}), 400
    
    audio_file = request.files['audio']
    
    # Save temporary file
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        audio_file.save(tmp.name)
        
        try:
            # Use session API
            results = transcribe_audio(tmp.name)
            return jsonify({'results': results})
        finally:
            os.unlink(tmp.name)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

This API documentation provides complete integration details for the hybrid session architecture, enabling developers to build efficient speech-to-text applications with optimal performance and resource management.