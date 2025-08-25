# GPU-Accelerated Speech-to-Text For Ubuntu

A high-performance Python speech-to-text system that uses INSERT key recording and GPU-accelerated offline transcription with Faster Whisper models. Designed for Ubuntu systems with NVIDIA GPU support.

> **Note**: This is an enhanced fork of [CDNsun/speech-to-text-for-ubuntu](https://github.com/CDNsun/speech-to-text-for-ubuntu) with GPU acceleration, minimal refactoring, and production-ready features.

## Key Features

- 🚀 **Hybrid Session Architecture**: 82% faster with smart VRAM management (1.6s → 0.3s for cached requests)
- 🧠 **Smart Memory Management**: Model persists during active use, auto-releases VRAM after 10min inactivity
- 🎯 **High Accuracy**: large-v3 Whisper model for best transcription quality  
- ⌨️ **INSERT Key Trigger**: Simple hold-to-record, release-to-transcribe
- 🔧 **No Sudo Required**: Uses pynput for X11 key listening
- 📝 **Auto-typing**: Transcribed text automatically appears in active window
- 🐧 **Linux Optimized**: Tested on Ubuntu 24.04.2 LTS with CUDA 12.9

## Quick Demo

```bash
# 1. Start the system
./venv/bin/python3 src/key_listener.py

# 2. Hold INSERT key and speak: "Hello, this is a test"
# 3. Release INSERT key
# 4. See "Hello, this is a test" typed automatically
#    - First request: ~1.6s (includes model loading)
#    - Subsequent requests: ~0.3s (cached model)
```

## System Requirements

- **OS**: Ubuntu 24.04+ (or compatible Linux with X11)
- **GPU**: NVIDIA GPU with CUDA 12.0+ support  
- **RAM**: 4GB+ (3GB VRAM for GPU model)
- **Python**: 3.10+
- **Audio**: Working microphone and `arecord` utility

## Installation

### 1. Clone and Setup

```bash
git clone https://github.com/sati-bodhi/gpu-accelerated-speech-to-text-for-ubuntu.git
cd gpu-accelerated-speech-to-text-for-ubuntu
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies  

```bash
# Install locked dependencies (69 packages with exact versions)
pip install -r requirements.txt

# Install system audio tools
sudo apt install alsa-utils
```

### 4. Verify GPU Support

```bash
nvidia-smi  # Should show your GPU
python3 -c "import torch; print('CUDA available:', torch.cuda.is_available())"

# Test the session system
echo "Testing session architecture..."
timeout 3s arecord -f S16_LE -r 16000 -c 1 test_audio.wav
./scripts/run_gpu_speech_session.sh test_audio.wav
```

### 5. Session System Setup

The hybrid session architecture requires proper CUDNN library paths:

```bash
# Verify CUDNN libraries are installed
ls venv/lib/python3.10/site-packages/nvidia/cudnn/lib/
ls venv/lib/python3.10/site-packages/nvidia/cublas/lib/

# Test session daemon manually (optional)
./venv/bin/python3 src/session_daemon.py &
sleep 5
cat /tmp/session_daemon_status.json
pkill -f session_daemon.py
```

## Usage

### Interactive Mode (Recommended)

Start the key listener for hands-free operation:

```bash
./venv/bin/python3 src/key_listener.py
```

**Controls:**
- **Hold INSERT key**: Start recording (you'll see logging activity)
- **Release INSERT key**: Stop recording and process with session daemon
- **Ctrl+C**: Exit the program (persistent by design, no ESC exit)

### Direct Processing

Test the hybrid session system with an audio file:

```bash
# Record a test file first
arecord -f cd -t wav -d 5 test.wav

# Process with hybrid session (recommended)
./scripts/run_gpu_speech_session.sh test.wav

# Or use direct processing (no session caching)
./scripts/run_gpu_speech.sh test.wav
```

## Performance

### Hybrid Session Architecture

| Scenario | Processing Time | VRAM Usage | Notes |
|----------|----------------|------------|-------|
| **First Request (Cold Start)** | ~1.6s | 3GB allocated | Includes model loading |
| **Subsequent Requests (Cached)** | ~0.3s | 3GB maintained | 82% faster with session persistence |
| **After 10min Inactivity** | Auto-releases | 0GB | Smart VRAM management |
| **CPU Fallback** | ~9.8s | 0GB | Automatic if no GPU |

### Key Improvements
- **🔥 82% Performance Gain**: Session persistence eliminates repeated model loading
- **🧠 Smart VRAM Management**: Only uses 3GB during active sessions
- **⚡ Sub-second Transcription**: Cached model processes audio in ~0.3s
- **🔄 Auto-shutdown**: Releases VRAM after 10 minutes of inactivity

**Accuracy**: Excellent with large-v3 model (same quality as OpenAI's commercial service)

## Architecture

### Hybrid Session Implementation

The system uses a **hybrid session architecture** that balances performance with resource efficiency:

```
├── src/
│   ├── key_listener.py           # INSERT key listener (client)
│   ├── session_daemon.py         # Smart session daemon with auto-shutdown
│   └── gpu_service_hybrid.py     # Optimized cold-start service
├── scripts/
│   ├── run_gpu_speech_session.sh # Session-aware client wrapper
│   └── run_gpu_speech.sh         # Original GPU wrapper (fallback)
├── requirements.txt              # Locked dependencies
├── README.md                     # This file
├── ARCHITECTURE.md               # Hybrid session architecture details
├── SESSION_API.md                # Complete API reference for developers
├── CLAUDE.md                     # Developer documentation
├── ARCHITECTURE_ANALYSIS.md      # Technical analysis
└── LICENSE.md                    # MIT License
```

### Session Processing Flow

```
INSERT Key → Key Listener → Audio Recording → Session Client
     ↓
JSON Request → Session Daemon → Cached Model → Transcription
     ↓
JSON Response → Auto-typing → File Cleanup → Session Extended (10min)
```

### Smart VRAM Management

- **On-demand Loading**: Model loads only on first request
- **Session Persistence**: Model stays cached during active use  
- **Auto-shutdown**: Releases 3GB VRAM after 10 minutes of inactivity
- **IPC Communication**: File-based JSON requests/responses in `/tmp/`

## Key Dependencies

- **faster-whisper==1.2.0**: Speech recognition engine
- **ctranslate2==4.6.0**: GPU acceleration backend
- **nvidia-cudnn-cu12==9.12.0.46**: CUDNN for GPU processing  
- **pynput==1.8.1**: X11 key listener (no sudo required)
- **pyautogui==0.9.54**: Automatic text typing

## Troubleshooting

### CUDNN Library Issues

If you see `"Unable to load libcudnn_ops.so.9.1.0"`:
- The session wrapper auto-sets library paths on daemon startup
- Verify your virtual environment path in `scripts/run_gpu_speech_session.sh`
- Ensure CUDA 12.0+ is properly installed
- Restart the session daemon if issues persist: `pkill -f session_daemon.py`

### Key Listener Not Working

- Ensure you're running X11 (not Wayland): `echo $XDG_SESSION_TYPE`
- Virtual environment activated: `which python3` should show venv path
- pynput installed: `pip list | grep pynput`

### Session Daemon Issues

If transcription is slow or timing out:
- Check daemon status: `cat /tmp/session_daemon_status.json`
- View daemon logs: `tail -f /tmp/session_daemon.log`
- Restart daemon: `pkill -f session_daemon.py` (will auto-restart on next request)
- Clear stale requests: `rm -f /tmp/speech_session_requests/*.json`

### GPU Not Detected

- Check NVIDIA drivers: `nvidia-smi`
- Verify CUDA installation: `nvcc --version`
- System automatically falls back to CPU if GPU unavailable

### Audio Recording Issues

- Test microphone: `arecord -f cd -t wav -d 2 test.wav && aplay test.wav`
- Check audio permissions and device access
- Ensure `alsa-utils` is installed

## Auto-Start on Login

Automatically start the listener when you log in using the provided installer:

```bash
# Run the auto-start installer
./scripts/install_autostart.sh
```

The installer will:
- ✅ **Add auto-start code** to your `~/.bashrc`
- ✅ **Check for duplicates** (prevents multiple instances)
- ✅ **Verify installation** (checks paths and dependencies)
- ✅ **Provide test option** (immediate verification)

**Features of auto-start:**
- Triggers on new terminals, SSH sessions, system reboot
- Background process with `nohup` (survives logout)
- Logs to `/tmp/speech_listener.log` for debugging
- Smart duplicate prevention

**Manual Controls:**
```bash
# Check if running
pgrep -f "src/key_listener.py"

# Stop listener
pkill -f "src/key_listener.py"

# View logs
tail -f /tmp/speech_listener.log

# Uninstall: Edit ~/.bashrc and remove the auto-start section
```

## Configuration

### Custom Key Binding

To change from INSERT key to another key, edit `src/key_listener.py`:

```python
# Line 97: Change keyboard.Key.insert to your preferred key
if key == keyboard.Key.f12:  # Example: Use F12 instead
```

### Model Selection

To use a different Whisper model, edit `src/gpu_service.py`:

```python
# Line 70: Change model size
model_size = "medium.en"  # Options: base.en, small.en, medium.en, large-v3
```

## Development

This codebase was refactored from 55+ files to 8 essential files for maintainability. 

**Key Points:**
- All original functionality preserved in git history
- Focus development on the 8 core files
- Run `tail -f /tmp/speech_to_text.log` to monitor processing
- Test changes with both direct calls and key listener integration

## Documentation

### 📚 Complete Documentation Suite

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Comprehensive technical details of the hybrid session implementation
- **[SESSION_API.md](SESSION_API.md)** - Complete API reference for developers and integration
- **[CLAUDE.md](CLAUDE.md)** - Development guidance and project methodology
- **[ARCHITECTURE_ANALYSIS.md](ARCHITECTURE_ANALYSIS.md)** - Technical analysis of optimization process

### 🔍 Key Topics Covered

**ARCHITECTURE.md**: Session daemon lifecycle, IPC protocol, VRAM management, performance benchmarks, monitoring and debugging

**SESSION_API.md**: JSON request/response formats, client implementation examples, error handling, daemon management, integration patterns

See these documents for detailed development guidance and system integration.

## Attribution

This project is an enhanced fork of the original [speech-to-text-for-ubuntu](https://github.com/CDNsun/speech-to-text-for-ubuntu) by CDNsun.

**Original Project**: Copyright (c) 2025 CDNsun s.r.o.  
**Enhanced Fork**: Adds GPU acceleration, minimal architecture, auto-start installer, and production features.

## License

MIT License - see `LICENSE.md` for details.

This project maintains the original MIT license from CDNsun and includes all required copyright notices.

## Performance History

This system was extensively optimized for both accuracy and speed:
- **Token optimization**: Reduced Claude correction costs by 99.8%  
- **GPU acceleration**: 3.6x speed improvement over CPU
- **CUDNN integration**: Resolved library compatibility issues
- **Minimal refactoring**: 85% file reduction while preserving functionality

See `ARCHITECTURE_ANALYSIS.md` for detailed technical analysis of the optimization process.

---

**🎯 Ready to use**: Hold INSERT, speak clearly, release INSERT, and watch your words appear!