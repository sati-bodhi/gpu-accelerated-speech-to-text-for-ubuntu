# GPU-Accelerated Speech-to-Text For Ubuntu

A high-performance Python speech-to-text system that uses INSERT key recording and GPU-accelerated offline transcription with Faster Whisper models. Designed for Ubuntu systems with NVIDIA GPU support.

> **Note**: This is an enhanced fork of [CDNsun/speech-to-text-for-ubuntu](https://github.com/CDNsun/speech-to-text-for-ubuntu) with GPU acceleration, minimal refactoring, and production-ready features.

## Key Features

- 🚀 **GPU Acceleration**: 3.6x faster than CPU (RTX 4060: ~2.7s vs CPU: ~9.8s)
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
# 4. See "Hello, this is a test" typed automatically (~2.7s later)
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
```

## Usage

### Interactive Mode (Recommended)

Start the key listener for hands-free operation:

```bash
./venv/bin/python3 src/key_listener.py
```

**Controls:**
- **Hold INSERT key**: Start recording (you'll see logging activity)
- **Release INSERT key**: Stop recording and process with GPU
- **ESC key**: Exit the program

### Direct Processing

Test the GPU service with an audio file:

```bash
# Record a test file first
arecord -f cd -t wav -d 5 test.wav

# Process with GPU acceleration  
./scripts/run_gpu_speech.sh test.wav
```

## Performance

| Component | Time | Notes |
|-----------|------|--------|
| **GPU Model Loading** | ~2.0s | One-time per transcription |
| **GPU Transcription** | ~0.7s | For 5-second audio |
| **Total Processing** | ~2.7s | Complete pipeline |
| **CPU Fallback** | ~9.8s | Automatic if no GPU |

**Accuracy**: Excellent with large-v3 model (same quality as OpenAI's commercial service)

## Architecture

### Minimal Structure (8 Files)

```
├── src/
│   ├── gpu_service.py          # Main GPU-accelerated service  
│   └── key_listener.py         # INSERT key listener
├── scripts/
│   └── run_gpu_speech.sh       # GPU environment wrapper
├── requirements.txt            # Locked dependencies
├── README.md                   # This file
├── CLAUDE.md                   # Developer documentation
├── ARCHITECTURE_ANALYSIS.md    # Technical analysis
└── LICENSE.md                  # MIT License
```

### Processing Flow

```
INSERT Key → pynput listener → arecord → GPU wrapper → CUDA processing → pyautogui typing
```

## Key Dependencies

- **faster-whisper==1.2.0**: Speech recognition engine
- **ctranslate2==4.6.0**: GPU acceleration backend
- **nvidia-cudnn-cu12==9.12.0.46**: CUDNN for GPU processing  
- **pynput==1.8.1**: X11 key listener (no sudo required)
- **pyautogui==0.9.54**: Automatic text typing

## Troubleshooting

### CUDNN Library Issues

If you see `"Unable to load libcudnn_ops.so.9.1.0"`:
- The system should auto-resolve this via the wrapper script
- Verify your virtual environment path in `scripts/run_gpu_speech.sh`
- Ensure CUDA 12.0+ is properly installed

### Key Listener Not Working

- Ensure you're running X11 (not Wayland): `echo $XDG_SESSION_TYPE`
- Virtual environment activated: `which python3` should show venv path
- pynput installed: `pip list | grep pynput`

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

See `CLAUDE.md` for detailed development guidance.

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