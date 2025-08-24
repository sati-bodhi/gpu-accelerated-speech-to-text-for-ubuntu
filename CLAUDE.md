# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a GPU-accelerated speech-to-text system for Ubuntu that uses INSERT key recording and offline transcription with Faster Whisper models. The system records audio on key press/release and transcribes speech using AI models with CUDA acceleration for high-speed, high-accuracy transcription.

## Minimal Architecture (Refactored)

This codebase has been refactored from 55+ files to 8 essential files for maintainability and clarity.

### Directory Structure

```
/home/sati/speech-to-text-for-ubuntu/
├── src/
│   ├── gpu_service.py      # Main GPU-accelerated speech service
│   └── key_listener.py     # INSERT key listener with pynput
├── scripts/
│   └── run_gpu_speech.sh   # GPU wrapper with CUDNN environment setup
├── requirements.txt        # Locked dependencies (69 packages)
├── README.md              # User documentation  
├── CLAUDE.md              # Development guidance (this file)
├── ARCHITECTURE_ANALYSIS.md # Technical analysis and history
└── LICENSE.md             # MIT License
```

### Core Components

**Key Listener** (`src/key_listener.py`):
- X11-compatible using pynput (no sudo required)
- INSERT key trigger for recording
- Automatic audio file cleanup after processing
- Error handling and logging

**GPU Service** (`src/gpu_service.py`):
- CUDA-accelerated Faster Whisper large-v3 model
- Proper CUDNN library path setup
- Automatic GPU/CPU fallback
- Audio preprocessing (stereo→mono conversion)
- pyautogui text output integration

**Environment Wrapper** (`scripts/run_gpu_speech.sh`):
- CUDNN and CUBLAS library path configuration
- Resolves "Unable to load libcudnn_ops.so.9.1.0" errors
- Enables GPU acceleration in subprocess calls

### Production Flow
```
INSERT key press → pynput listener → arecord → GPU wrapper script → CUDA processing → pyautogui typing
```

## Performance Characteristics

- **GPU Model**: RTX 4060 with CUDA 12.9
- **Processing Time**: ~2.7s (2.0s model load + 0.7s transcription)
- **Model**: large-v3 for highest accuracy
- **Speed Improvement**: 3.6x faster than CPU processing
- **Memory Usage**: ~3GB VRAM for model

## Common Commands

### Running the System

**Start Key Listener**:
```bash
./venv/bin/python3 src/key_listener.py
```

**Test GPU Service Directly**:
```bash
./scripts/run_gpu_speech.sh /path/to/audio.wav
```

**Install Dependencies** (locked versions):
```bash
pip install -r requirements.txt
```

**Install Auto-start** (optional):
```bash
./scripts/install_autostart.sh
```

### Development Commands

**Check GPU Status**:
```bash
nvidia-smi
python3 -c "import torch; print('CUDA available:', torch.cuda.is_available())"
```

**View Recent Logs**:
```bash
tail -f /tmp/speech_to_text.log
tail -f /tmp/key_listener.log
```

## Key Configuration Points

### File Paths (src/key_listener.py:79)
```python
subprocess.run([
    "/home/sati/speech-to-text-for-ubuntu/scripts/run_gpu_speech.sh",
    current_audio_file
], check=True)
```

### Environment Setup (scripts/run_gpu_speech.sh:5-17)
```bash
VENV_PATH="/home/sati/speech-to-text-for-ubuntu/venv"
CUDNN_LIB="$VENV_PATH/lib/python3.10/site-packages/nvidia/cudnn/lib"
CUBLAS_LIB="$VENV_PATH/lib/python3.10/site-packages/nvidia/cublas/lib"
export LD_LIBRARY_PATH="$CUDNN_LIB:$CUBLAS_LIB:$LD_LIBRARY_PATH"
```

## Dependencies (Locked)

Core dependencies with exact versions:
- **faster-whisper==1.2.0** - Speech recognition engine
- **ctranslate2==4.6.0** - GPU acceleration backend  
- **nvidia-cudnn-cu12==9.12.0.46** - CUDNN for GPU processing
- **nvidia-cublas-cu12==12.9.1.4** - CUDA math libraries
- **pynput==1.8.1** - X11 key listener
- **pyautogui==0.9.54** - Text output automation
- **numpy==2.2.6** - Numerical processing
- **soundfile==0.13.1** - Audio file handling

## Troubleshooting

### CUDNN Library Errors
If you see "Unable to load libcudnn_ops.so.9.1.0":
- The wrapper script should handle this automatically
- Verify venv path in `scripts/run_gpu_speech.sh`
- Check CUDA installation with `nvidia-smi`

### Key Listener Issues
- Ensure X11 session is running (not Wayland)
- No sudo required with pynput version
- Check pynput installation in virtual environment

### GPU Fallback
- System automatically falls back to CPU if GPU unavailable
- CPU processing takes ~9.8s vs ~2.7s GPU
- Same accuracy with both backends

## Git Workflow

This repository uses git branches for major changes:
- **main**: Original complex codebase (preserved in history)
- **refactor-minimal**: Current clean, minimal implementation

To recover any historical files:
```bash
git checkout HEAD~2 -- old_filename.py  # Recover from previous commits
git log --name-status                    # See what was changed
```

## Development Notes

- The system maintains 100% functionality from the original complex codebase
- All 55+ original files are preserved in git history
- Focus on the 8 core files for any modifications
- Test changes with both direct service calls and key listener integration
- Always verify GPU acceleration is working after changes (`Using CUDA with large-v3 model` in logs)

## Architecture History

See `ARCHITECTURE_ANALYSIS.md` for detailed technical analysis including:
- Token consumption optimization attempts  
- Failed architecture experiments and reasons
- Performance comparisons between approaches
- Lessons learned from the development process