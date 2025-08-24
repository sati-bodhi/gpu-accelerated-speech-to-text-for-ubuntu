#!/bin/bash
# Test script to demonstrate auto-start behavior

echo "🧪 Testing Speech-to-Text Auto-start Logic"
echo "============================================"

# Check current status
if pgrep -f "src/key_listener.py" > /dev/null; then
    echo "✅ Listener is currently running (PID: $(pgrep -f 'src/key_listener.py'))"
    echo "📋 Auto-start logic will detect this and skip starting another instance"
else
    echo "❌ Listener is not running"
    echo "📋 Auto-start logic would start the listener automatically"
fi

echo
echo "📂 Log file location: /tmp/speech_listener.log"
if [ -f "/tmp/speech_listener.log" ]; then
    echo "📄 Recent log entries:"
    tail -5 /tmp/speech_listener.log
else
    echo "📄 No log file exists yet"
fi

echo
echo "🔧 Manual controls:"
echo "  Kill listener:  pkill -f 'src/key_listener.py'"
echo "  Check status:   pgrep -f 'src/key_listener.py'"
echo "  View logs:      tail -f /tmp/speech_listener.log"
echo
echo "🔄 Auto-start will trigger on:"
echo "  • New terminal window"
echo "  • SSH login"
echo "  • System reboot (after login)"
echo "  • Any new bash session"