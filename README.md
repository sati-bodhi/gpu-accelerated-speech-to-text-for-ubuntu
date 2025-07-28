# Speech-to-Text For Ubuntu

A simple Python project to record audio using a hotkey (such as a remapped mouse button) and automatically transcribe it to text using a speech-to-text Faster Whisper model. Designed for use on Linux systems (tested on Ubuntu 24.04.2 LTS).

## Project Overview

- **key_listener.py**: Monitors a designated key (such as F16, which can be mapped to a mouse button or to any other key) to control audio recording. Recording begins when the key is pressed and ends upon release, at which point speech-to-text processing is automatically initiated.

- **speech_to_text.py**: Loads the recorded audio, processes it (converts stereo to mono if needed), and transcribes the speech to text using the Faster Whisper model.

## Requirements

- Python 3.x
- Linux (tested on Ubuntu 24.04.2 LTS)
- Python virtual environment with required packages installed (see below)
- `arecord` (for audio recording)
- `evdev` (for key listening)
- A speech-to-text model (e.g., Faster Whisper)

## Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/CDNsun/speech-to-text-for-ubuntu
   cd speech-to-text-for-ubuntu
   ```
2. **Create and activate a Python virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
4. **Ensure you have `arecord` and `evdev` installed**
   ```bash
   sudo apt install alsa-utils python3-evdev
   ```
5. **Remap your mouse button to an unused key (e.g., F16) using input-remapper or similar tool.**

## Usage

### 1. Start the Key Listener

Run as root (required for input device access and sudo):
```bash
sudo python3 key_listener.py
```

- Press and hold your chosen key (e.g., F16/mouse button) to start recording.
- Release the key to stop recording and trigger speech-to-text.

For automatic start on boot you use crontab (for root) similar to this:
```
* * * * * ps -ef | grep "/home/david/Cursor/speech-to-text/key_listener.py" | grep -v grep > /dev/null || /usr/bin/python3 /home/david/Cursor/speech-to-text/key_listener.py >> /tmp/key_listener.log 2>&1 &
```

### 2. Speech-to-Text Script

This script is called automatically by `key_listener.py`, but you can also run it manually:
```bash
python3 speech_to_text.py /path/to/audio.wav
```

## How it Works

- **key_listener.py**
  - Listens for a specific key event using `evdev`.
  - Starts `arecord` to record audio when the key is pressed.
  - Stops recording when the key is released.
  - Calls `speech_to_text.py` to transcribe the recorded audio.
  

- **speech_to_text.py**
  - Loads the recorded audio file.
  - Converts stereo audio to mono if necessary.
  - Transcribes the audio to text using a speech-to-text Faster Whisper model.
  - Types the recognized text into the active window using `pyautogui`.

## Notes
- You may need to adjust device paths and user names in the scripts to match your system.
- The script assumes you have a Python virtual environment (e.g., `/home/david/venv/bin/python3`) with the necessary packages installed.


## License

MIT License

Copyright (c) 2025 CDNsun

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.