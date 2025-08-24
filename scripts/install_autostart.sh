#!/bin/bash
# Install Speech-to-Text Auto-start Service
# Adds auto-start code to user's .bashrc for automatic listener startup

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BASHRC="$HOME/.bashrc"

echo "🚀 Speech-to-Text Auto-start Installer"
echo "======================================"
echo "Project directory: $PROJECT_DIR"
echo "Target .bashrc: $BASHRC"
echo

# Check if project directory exists
if [ ! -d "$PROJECT_DIR/src" ]; then
    echo "❌ Error: Project directory not found or missing src/ folder"
    echo "   Expected: $PROJECT_DIR/src/"
    exit 1
fi

# Check if key_listener.py exists
if [ ! -f "$PROJECT_DIR/src/key_listener.py" ]; then
    echo "❌ Error: key_listener.py not found"
    echo "   Expected: $PROJECT_DIR/src/key_listener.py"
    exit 1
fi

# Check if virtual environment exists
if [ ! -f "$PROJECT_DIR/venv/bin/python3" ]; then
    echo "❌ Error: Virtual environment not found"
    echo "   Expected: $PROJECT_DIR/venv/bin/python3"
    echo "   Please run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Check if auto-start is already installed
if grep -q "src/key_listener.py" "$BASHRC" 2>/dev/null; then
    echo "⚠️  Auto-start already installed in .bashrc"
    echo
    read -p "Do you want to reinstall/update it? (y/N): " choice
    case "$choice" in
        [yY]|[yY][eS])
            # Remove existing entries
            echo "🔧 Removing existing auto-start entries..."
            # Create temporary file without the auto-start block
            awk '
                /# Start speech-to-text listener/ { skip=1 }
                /^fi$/ && skip { skip=0; next }
                !skip
            ' "$BASHRC" > "$BASHRC.tmp" && mv "$BASHRC.tmp" "$BASHRC"
            ;;
        *)
            echo "Installation cancelled."
            exit 0
            ;;
    esac
fi

# Create the auto-start code
AUTOSTART_CODE="
# Start speech-to-text listener if not already running
if ! pgrep -f \"src/key_listener.py\" > /dev/null; then
    cd $PROJECT_DIR
    nohup ./venv/bin/python3 src/key_listener.py > /tmp/speech_listener.log 2>&1 &
    echo \"Speech-to-text listener started\"
fi"

# Add to .bashrc
echo "📝 Adding auto-start code to .bashrc..."
echo "$AUTOSTART_CODE" >> "$BASHRC"

echo "✅ Auto-start successfully installed!"
echo

# Test the installation
echo "🧪 Testing installation..."
if grep -q "src/key_listener.py" "$BASHRC"; then
    echo "✅ Auto-start code found in .bashrc"
else
    echo "❌ Installation verification failed"
    exit 1
fi

# Show usage information
echo
echo "📋 Installation Complete!"
echo "========================"
echo
echo "🔄 Auto-start will trigger on:"
echo "  • New terminal windows"
echo "  • SSH login sessions"  
echo "  • System reboot (after login)"
echo "  • Any new bash session"
echo
echo "🔧 Manual controls:"
echo "  Check status:    pgrep -f 'src/key_listener.py'"
echo "  Stop listener:   pkill -f 'src/key_listener.py'"
echo "  View logs:       tail -f /tmp/speech_listener.log"
echo
echo "🚀 To test immediately:"
echo "  1. Open a new terminal window"
echo "  2. You should see: 'Speech-to-text listener started'"
echo "  3. Try holding INSERT key and speaking"
echo
echo "⚙️  To uninstall later:"
echo "  Edit ~/.bashrc and remove the 'Start speech-to-text listener' section"

echo
read -p "🧪 Test now by opening a new bash session? (y/N): " test_choice
case "$test_choice" in
    [yY]|[yY][eS])
        echo
        echo "🔄 Testing in new bash session..."
        bash -l -c 'echo "New session started - auto-start should have triggered above"'
        ;;
    *)
        echo "Test skipped. Open a new terminal to test auto-start."
        ;;
esac