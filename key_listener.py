#!/usr/bin/env python3
"""
Audio Recording Key Listener

This script listens for a specific key press to start audio recording and stops on key release.
In other words, it listens and records when the key is pressed and stops when the key is released.

It is recommended to use a key (I use F16) that is not otherwise used by your system or 
applications, otherwise you may experience interference.

For example, suppose you want to use the side mouse button (BTN_SIDE) to trigger speech-to-text.
However, some programs (such as Chrome) already use this button for navigation (e.g., "back").
To avoid conflicts, you can use input-remapper-gtk to remap BTN_SIDE to F16 (which is typically 
not used by any program).

This script must be run as root in order to access input devices (e.g., /dev/input/event*).
Running as a regular user will result in permission errors.

To automatically start this key listener on boot, you can use the following crontab entry for root:

* * * * * ps -ef | grep "/home/david/Cursor/speech-to-text/key_listener.py" | grep -v grep > /dev/null || /usr/bin/python3 /home/david/Cursor/speech-to-text/key_listener.py >> /tmp/key_listener.log 2>&1 &

This cron job checks every minute if the key_listener.py script is running. If it is not, it starts the script.
The output and errors are appended to /tmp/key_listener.log.

Usage (as root): python3 key_listener.py

Tested on Ubuntu 24.04.2 LTS

The script assumes that the user has a python virtual environment in /home/david/venv/bin/python3
with the necessary packages installed including evdev, numpy pyautogui soundfile faster-whisper
"""

import logging
import os
import sys
import subprocess
import pwd


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/key_listener.log')
    ]
)

try:
    from evdev import InputDevice, categorize, ecodes
except ImportError:
    print("Error: evdev library not found. Install in your venv with: pip install evdev")
    sys.exit(1)

# Configuration
# To choose the correct event ID for your device, use the `evtest` tool:
# Run `sudo evtest` in a terminal.
# If you used input-remapper-gtk then it can look like this: 
# /dev/input/event12:     input-remapper keyboard
DEVICE_PATH = "/dev/input/event2"

# Just a temporary file to store the audio. 
AUDIO_FILE = "/tmp/recorded_audio.wav"

# The user who runs the X server accessing the microphone. 
USER = "sati"

# We will get XAUTHORITY variable from a running process (e.g., /usr/bin/ksmserver) owned by USER.
# Find a process that is always running in single instance and owned by USER and has 
# XAUTHORITY variable defined in its environment (see /proc/{pid}/environ)
PROCESS_FOR_XAUTH_COPY = "/usr/libexec/gnome-session-binary"

# The script that will process the stored audio and generate text from it. 
SPEECHTOTEXT_SCRIPT = "/home/sati/speech-to-text-for-ubuntu/speech_to_text.py"

# Your python virtual environment
PYTHON_VENV = "/home/sati/speech-to-text-for-ubuntu/venv/bin/python3"

def setup_environment():
    pw_record = pwd.getpwnam(USER)
    env = os.environ.copy()
    env.update({
        "HOME": f"/home/{USER}",
        "XDG_CACHE_HOME": f"/home/{USER}/.cache",
        "XDG_RUNTIME_DIR": f"/run/user/{pw_record.pw_uid}",
        "DISPLAY": ":0"
    })

    # Get XAUTHORITY from the environment of the running process 
    # PROCESS_FOR_XAUTH_COPY owned by USER.
    # If your XAUTHORITY is simply ~/.Xauthority, then you can skip this step
    # and set env["XAUTHORITY"] = "~/.Xauthority"
    # Check your confiuration using: echo $XAUTHORITY (as USER)
    try:
        # Use pgrep to get the PID of the process
        pid = subprocess.check_output(
            ["pgrep", "-u", USER, "-f", PROCESS_FOR_XAUTH_COPY],
            universal_newlines=True
        ).strip().split('\n')[0]
        environ_path = f"/proc/{pid}/environ"
        with open(environ_path, "rb") as f:
            env_vars = f.read().split(b'\0')
            xauth = None
            for var in env_vars:
                if var.startswith(b"XAUTHORITY="):
                    xauth = var[len(b"XAUTHORITY="):].decode()
                    break
        if not xauth:
            raise RuntimeError(f"XAUTHORITY not found in environment of process {PROCESS_FOR_XAUTH_COPY} (PID {pid})")
        env["XAUTHORITY"] = xauth
        logging.info(f"Set XAUTHORITY to {xauth} (from process {PROCESS_FOR_XAUTH_COPY}, PID {pid})")
    except Exception as e:
        logging.error(f"Could not get XAUTHORITY from process {PROCESS_FOR_XAUTH_COPY} for {USER}: {e}")
        sys.exit(1)

    return env

def main():
    """Main function."""
    # Check if running as root
    if os.geteuid() != 0:
        logging.error("This script must be run as root")
        sys.exit(1)
    
    # Setup
    env = setup_environment()
    device = InputDevice(DEVICE_PATH)
    recording_process = None
    
    logging.info(f"Listening for KEY_INSERT on {DEVICE_PATH}")
    
    try:
        for event in device.read_loop():
            if event.type == ecodes.EV_KEY:
                key = categorize(event)
                
                # Ignore key repeats
                if key.keystate == 2:
                    continue
                
                if key.keycode == 'KEY_INSERT':
                    if key.keystate == key.key_down and recording_process is None:
                        # Start recording
                        logging.info("Starting audio recording")
                        recording_process = subprocess.Popen([
                            "sudo", "-u", USER, "-E",
                            "arecord",
                            "-f", "S16_LE", # nothing to do with KEY_F16
                            "-r", "16000",
                            "-c", "1",
                            AUDIO_FILE
                        ], env=env)
                        logging.info(f"Recording started with PID {recording_process.pid}")
                    
                    elif key.keystate == key.key_up and recording_process:
                        # Stop recording and process
                        logging.info("Stopping audio recording")
                        recording_process.terminate()
                        recording_process.wait()
                        logging.info(f"Recording saved to {AUDIO_FILE}")
                        
                        # Process audio
                        logging.info("Running speech-to-text")
                        subprocess.run([
                            "sudo", "-u", USER, "-E",
                            PYTHON_VENV,
                            SPEECHTOTEXT_SCRIPT,
                            AUDIO_FILE
                        ], env=env, check=True)
                        logging.info("Speech-to-text completed")
                        
                        recording_process = None
                        
    except KeyboardInterrupt:
        logging.info("Shutting down due to keyboard interrupt")
        if recording_process:
            recording_process.terminate()
    except Exception as e:
        logging.error(f"Error: {e}")

if __name__ == "__main__":
    main()

