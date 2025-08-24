---
allowed-tools: Bash
description: Refresh speech-to-text context by restarting daemon with new context capture
model: claude-3-5-haiku-20241022
---

Refresh the speech-to-text correction context by restarting the daemon.

!echo "🔄 Refreshing speech-to-text context..."

# Kill existing daemon if running
!pkill -f speech_daemon.py 2>/dev/null && echo "✓ Stopped existing daemon" || echo "ℹ️ No daemon was running"

# Start daemon with fresh context capture
!echo "🚀 Starting daemon with fresh context capture..."
!cd /home/sati/speech-to-text-for-ubuntu && nohup /home/sati/speech-to-text-for-ubuntu/venv/bin/python3 speech_daemon.py > /tmp/speech_daemon.log 2>&1 & echo "✅ Daemon started with PID $!"

!echo "📝 Daemon will capture new context on startup (~20-30s)"
!echo "🎯 Speech corrections will use updated context for better accuracy"
!sleep 2 && tail -5 /tmp/speech_daemon.log