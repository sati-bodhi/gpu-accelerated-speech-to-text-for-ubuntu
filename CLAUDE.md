# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a GPU-accelerated speech-to-text system for Ubuntu that uses INSERT key recording and offline transcription with Faster Whisper models. The system records audio on key press/release and transcribes speech using AI models with CUDA acceleration for high-speed, high-accuracy transcription.

## Modern Modular Architecture with Production Safety

This system uses a modern modular session-based daemon architecture with advanced audio preprocessing, built-in safety mechanisms, and optimal speech recognition performance.

### Directory Structure

```
/home/sati/speech-to-text-for-ubuntu/
├── src/
│   ├── session_daemon.py         # Modern modular session daemon (production ready)
│   ├── audio_processor.py        # Audio preprocessing and noise cancelling service
│   ├── speech_engine.py          # Whisper speech recognition engine service
│   ├── session_coordinator.py    # Session lifecycle and timeout management service  
│   ├── text_output.py            # Text typing and correction output service
│   └── key_listener.py           # INSERT key listener with hybrid session support
├── scripts/
│   ├── run_gpu_speech_session.sh # Hybrid session wrapper with ping-pong testing
│   └── type_correction.py        # LLM correction output helper
├── requirements.txt               # Locked dependencies (scipy, faster-whisper, etc.)
├── README.md                     # User documentation  
├── CLAUDE.md                     # Development guidance (this file)
├── ARCHITECTURE_ANALYSIS.md      # Technical analysis and history
└── LICENSE.md                    # MIT License
```

### Core Components

**Modern Session Daemon** (`src/session_daemon.py`) **[Production Ready]**:
- **Modular Architecture**: Clean separation of concerns using focused services
- **Thin Orchestration**: Service coordination layer with minimal overhead
- **AudioPreprocessor**: Noise cancelling, content validation, and JSON-safe audio analysis
- **SpeechEngine**: Whisper model management with type-safe transcription results
- **SessionCoordinator**: Activity tracking, timeout management, and session lifecycle
- **TextOutputManager**: Typing automation and correction handling
- **Built-in Safety**: Infinite loop protection and emergency shutdown mechanisms
- **Enhanced Logging**: Rich metadata and comprehensive error tracking

**Key Listener** (`src/key_listener.py`):
- X11-compatible using pynput (no sudo required)
- INSERT key trigger with hybrid session integration
- Automatic audio file cleanup and error handling
- Seamless daemon communication via IPC

**Hybrid Session Wrapper** (`scripts/run_gpu_speech_session.sh`):
- Ping-pong daemon responsiveness testing
- Automatic daemon startup with startup locks
- CUDNN library path configuration
- Session timeout and health monitoring

### Production Flow
```
INSERT key → pynput listener → arecord → hybrid session wrapper → 
session daemon (with noise cancelling) → VAD-optimized transcription → pyautogui typing
```

## Performance Characteristics

### Session Performance
- **Initial Load**: 2.2s (model loading + VRAM allocation)
- **Cached Processing**: 0.024s transcription (model stays loaded)
- **Session Timeout**: 10 minutes of inactivity before VRAM release
- **Responsiveness**: Ping-pong testing prevents false daemon restarts
- **Safety Protection**: Automatic shutdown after 3 consecutive request failures

### Audio Optimization Results
- **Noise Cancelling**: High-pass filter (80Hz) + spectral subtraction
- **VAD Threshold**: 0.16 (calibrated just above ambient RMS of 0.159)
- **Phoneme Preservation**: ~50% reduction in initial consonant cutting
- **Hardware Limitation**: Consumer-grade Realtek ALC257 (no built-in noise cancelling)
- **Processing Improvement**: From 5-6s timeout issues to consistent 1-2s transcription

## Common Commands

### Running the System

**Start Key Listener** (with hybrid session):
```bash
./venv/bin/python3 src/key_listener.py
```

**Test Session Daemon Directly**:
```bash
./scripts/run_gpu_speech_session.sh /path/to/audio.wav
```

**Start Session Daemon Manually** (for debugging):
```bash
./venv/bin/python3 src/session_daemon.py [timeout_seconds]
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
tail -f /tmp/session_daemon.log     # Session daemon activity
tail -f /tmp/key_listener.log       # Key listener events
cat /tmp/session_daemon_status.json # Current daemon status
```

**Test Ambient Sound Analysis**:
```bash
arecord -f S16_LE -r 16000 -c 1 -d 5 /tmp/ambient_test.wav
./venv/bin/python3 /tmp/analyze_ambient.py  # Analyze RMS levels for VAD tuning
```

## Key Configuration Points

### Critical VAD Settings (src/speech_engine.py:VADParameters)
```python
vad_parameters=dict(
    threshold=0.16,  # Just above early ambient RMS (0.159) for optimal speech detection
    min_silence_duration_ms=500,
    min_speech_duration_ms=100
)
```

### Noise Cancelling Implementation (src/audio_processor.py:apply_noise_cancelling)
```python
def apply_noise_cancelling(self, audio, sample_rate):
    # 1. High-pass filter (80Hz cutoff for AC hum/rumble removal)
    # 2. Spectral subtraction (conservative noise reduction)  
    # 3. Normalization (prevent clipping while preserving dynamics)
    # 4. JSON-safe type conversion for serialization compatibility
```

### Safety Mechanisms (src/session_daemon.py:process_request)
```python
# Infinite loop protection with automatic shutdown
if request_id in self.request_failure_count:
    self.request_failure_count[request_id] += 1
    if self.request_failure_count[request_id] > self.max_request_failures:
        self.logger.error(f"Emergency shutdown - preventing infinite loop")
        self.shutdown_requested = True
```

### Session Daemon Integration (src/key_listener.py:79)
```python
subprocess.run([
    "/home/sati/speech-to-text-for-ubuntu/scripts/run_gpu_speech_session.sh",
    current_audio_file
], check=True)
```

## Dependencies (Locked)

Core dependencies with exact versions:
- **faster-whisper==1.2.0** - Speech recognition engine with VAD
- **ctranslate2==4.6.0** - GPU acceleration backend  
- **scipy==1.15.3** - Signal processing for noise cancelling
- **nvidia-cudnn-cu12==9.12.0.46** - CUDNN for GPU processing
- **nvidia-cublas-cu12==12.9.1.4** - CUDA math libraries
- **pynput==1.8.1** - X11 key listener (no sudo required)
- **pyautogui==0.9.54** - Text output automation
- **numpy==2.2.6** - Numerical processing and FFT operations
- **soundfile==0.13.1** - Audio file I/O with debug output

## Troubleshooting

### Audio Quality Issues
**Phoneme Cutting (First Words Missing)**:
- Check VAD threshold: Should be just above ambient RMS
- Test ambient sound: `arecord -d 5 /tmp/ambient_test.wav`
- Analyze levels: `./venv/bin/python3 /tmp/analyze_ambient.py`
- Current optimal threshold: 0.16 (based on RMS 0.159)

**Poor Recognition Quality**:
- Hardware limitation: Realtek ALC257 has no built-in noise cancelling
- Software compensation: High-pass filter + spectral subtraction active
- Professional hardware would provide 70-90% improvement vs current ~50%

### Session Daemon Issues
**Daemon Not Responsive**:
- Check ping-pong test: Built into wrapper script
- Manual status check: `cat /tmp/session_daemon_status.json`
- Kill stale daemon: `pkill -f session_daemon.py`
- Safety mechanism: Daemon auto-terminates after 3 consecutive failures

**Memory/VRAM Problems**:
- Session auto-shutdown: 10 minutes inactivity
- Manual cleanup: Daemon releases VRAM on timeout
- Monitor usage: `nvidia-smi` for GPU memory
- Emergency protection: Prevents infinite loops from exhausting resources

**JSON Serialization Errors** (Fixed in current version):
- All data types converted to JSON-compatible Python natives
- AudioAnalysis uses `float()`, `int()`, `bool()` conversions  
- TranscriptionResult ensures type safety for all fields

### Key Listener Issues
- Ensure X11 session is running (not Wayland)
- No sudo required with pynput version
- Check daemon communication via IPC files in `/tmp/speech_session_*`

## Git Workflow

This repository uses git branches for major optimizations:
- **main**: Stable release branch
- **llm-correction-v2**: Current development with noise cancelling + VAD optimization
- **audio-preprocessing-experiment**: Experimental noise cancelling branch (merged)

Recent major improvements:
```bash
git log --oneline -5  # View recent optimization commits
```

## Development Notes

- **Modern Architecture**: Modular daemon with service separation provides maintainability while preserving 3.6x speedup
- **Audio Optimization**: Combined noise cancelling + VAD tuning achieved ~50% phoneme preservation improvement  
- **Production Safety**: Built-in infinite loop protection and JSON serialization safety prevent system failures
- **Hardware Analysis**: Consumer Realtek ALC257 codec identified as bottleneck
- **Professional Upgrade Path**: $300-800 audio interface would provide 70-90% phoneme cutting reduction
- **Critical Thresholds**: VAD 0.16 calibrated against ambient RMS 0.159 for optimal speech detection
- **Processing Pipeline**: JSON-safe audio preprocessing → VAD filtering → CUDA transcription → type-safe output
- **Architectural Evolution**: Transformed from monolithic (519 lines) to modular (343 lines + services) architecture
- **Legacy Access**: Original daemon available via git history (commit 223c183) if needed for reference

## Architecture History

See `ARCHITECTURE_ANALYSIS.md` for detailed technical analysis including:
- Token consumption optimization attempts  
- Failed architecture experiments and reasons
- Performance comparisons between approaches
- Lessons learned from the development process