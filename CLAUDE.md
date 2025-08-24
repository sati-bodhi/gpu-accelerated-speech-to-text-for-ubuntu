# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a speech-to-text system for Ubuntu that uses hotkey recording and offline transcription with Faster Whisper models. The system records audio on key press/release and transcribes speech using AI models, with optional Claude correction for improved accuracy.

## Core Architecture

### Main Components

**Key Listeners**:
- `key_listener_pynput.py` - Primary X11 key listener using pynput (no sudo required)
- `key_listener.py` - Legacy evdev-based listener (requires root)

**Speech Processing Variants**:
- `speech_to_text_parallel.py` - Parallel processing with model caching and ThreadPoolExecutor
- `speech_to_text_large.py` - Large model for highest accuracy
- `speech_to_text_gpu.py` - GPU-accelerated processing
- `speech_daemon.py` - Persistent daemon with ~400MB RAM usage for performance

**Correction System**:
- `claude_context_parser.py` - Extracts conversation context from `~/.claude/projects/*/conversation.jsonl`
- `speech_to_text_claude_correction.py` - Claude-based transcript correction
- MCP servers for context management and token optimization

### Current Production Flow
```
INSERT key press → pynput listener → arecord → speech_to_text_large.py → Claude CLI correction → pyautogui typing
```

## Common Commands

### Environment Setup
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install system dependencies
sudo apt install alsa-utils python3-evdev
```

### Running Components

**Start Key Listener** (recommended):
```bash
python3 key_listener_pynput.py
```

**Manual Speech Processing**:
```bash
python3 speech_to_text_large.py /tmp/recorded_audio.wav
```

**Start Speech Daemon** (for performance):
```bash
python3 speech_daemon.py
```

### Testing

Run individual test files directly:
```bash
python3 test_complete_workflow.py
python3 test_listener_daemon_integration.py
python3 test_mcp_correction.py
```

### Docker Variants

Multiple Docker configurations available:
```bash
# Build CUDA version
docker build -f Dockerfile.cuda -t speech-cuda .

# Build simple CPU version  
docker build -f Dockerfile.simple -t speech-cpu .
```

## Architecture Variants & Trade-offs

### Current Working Setup
- **Approach**: Full Claude CLI context (`-c` flag)
- **Accuracy**: High
- **Cost**: ~284k tokens per correction (~$340)
- **Speed**: 3-5 seconds per correction

### Token Optimization Attempts
- **Limited Context**: 99.8% token reduction (650 tokens) but unreliable accuracy
- **MCP Persistence**: Failed due to Claude CLI subprocess limitations
- **Daemon Architecture**: Built but not integrated with key listener

## Key Configuration Points

### File Paths (key_listener_pynput.py:30-34)
```python
USER = "sati"
SPEECHTOTEXT_SCRIPT = "/home/sati/speech-to-text-for-ubuntu/speech_to_text_large.py"
PYTHON_VENV = "/home/sati/speech-to-text-for-ubuntu/venv/bin/python3"
```

### Model Configuration
- **Default**: `base.en` model for speed/accuracy balance
- **High accuracy**: `large-v3` model (slower, more accurate)
- **GPU**: CUDA support available in GPU variants

## Critical Issues & Limitations

### Context Extraction Problems
- Workspace detection heuristics are error-prone
- Cross-workspace contamination in conversation parsing
- Technical terminology accuracy issues with limited context

### Claude CLI Limitations
- Not designed for programmatic persistence
- No subprocess session support
- Interactive terminal assumptions cause timeout failures

## Architecture Documentation

See `ARCHITECTURE_ANALYSIS.md` for detailed technical analysis including:
- Token consumption crisis documentation
- Failed architecture attempts and reasons
- Performance comparisons between approaches
- Lessons learned from optimization attempts

## Development Notes

### Model Loading
- Models cache in memory for performance (~400MB for large models)
- Cold startup takes 2-3 seconds for model initialization
- Persistent daemon reduces this to <1 second

### Audio Processing
- Records using `arecord` to `/tmp/recorded_audio_{timestamp}.wav`
- Converts stereo to mono automatically if needed
- Uses `pyautogui` for text insertion into active window

### Dependencies
Core requirements in `requirements.txt`:
- `faster-whisper` - Speech recognition model
- `pyautogui` - Text insertion
- `soundfile`, `numpy` - Audio processing
- `evdev` - Low-level input handling (legacy)