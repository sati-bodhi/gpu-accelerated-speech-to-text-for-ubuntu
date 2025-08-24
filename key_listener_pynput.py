#!/usr/bin/env python3
"""
Audio Recording Key Listener using pynput for X11 compatibility

This script listens for the Insert key to start/stop audio recording.
Works with X11 desktop environments using pynput instead of raw evdev.

Usage: python3 key_listener_pynput.py
Note: Does not require root/sudo since it uses X11 events
"""

import logging
import os
import sys
import subprocess
import signal
import time
from pynput import keyboard

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/key_listener.log')
    ]
)

# Configuration
AUDIO_FILE_TEMPLATE = "/tmp/recorded_audio_{}.wav"  # Timestamped to prevent repeated processing
USER = "sati"
SPEECHTOTEXT_SCRIPT = "/home/sati/speech-to-text-for-ubuntu/speech_to_text_gpu_fixed.py"  # GPU with fixed CUDNN library paths
PYTHON_VENV = "/home/sati/speech-to-text-for-ubuntu/venv/bin/python3"

# Global variables
recording_process = None
is_recording = False

def start_recording():
    """Start audio recording"""
    global recording_process, is_recording, current_audio_file
    
    if is_recording:
        return
    
    # Generate timestamped filename
    timestamp = int(time.time() * 1000)  # Millisecond precision
    current_audio_file = AUDIO_FILE_TEMPLATE.format(timestamp)
    
    logging.info("Starting audio recording")
    recording_process = subprocess.Popen([
        "arecord",
        "-f", "S16_LE",
        "-r", "16000",
        "-c", "1",
        current_audio_file
    ])
    is_recording = True
    logging.info(f"Recording started with PID {recording_process.pid} -> {current_audio_file}")

def stop_recording_and_process():
    """Stop recording and process audio"""
    global recording_process, is_recording, current_audio_file
    
    if not is_recording or recording_process is None:
        return
    
    logging.info("Stopping audio recording")
    recording_process.terminate()
    recording_process.wait()
    is_recording = False
    logging.info(f"Recording saved to {current_audio_file}")
    
    # Process audio with timestamped file
    logging.info("Running speech-to-text")
    try:
        subprocess.run([
            "/home/sati/speech-to-text-for-ubuntu/run_gpu_speech.sh",
            current_audio_file
        ], check=True)
        logging.info("Speech-to-text completed")
        
        # Cleanup old audio file after processing
        try:
            os.remove(current_audio_file)
            logging.info(f"Cleaned up {current_audio_file}")
        except OSError:
            pass  # File might not exist or already cleaned
            
    except subprocess.CalledProcessError as e:
        logging.error(f"Speech-to-text failed: {e}")
    
    recording_process = None

def on_press(key):
    """Handle key press events"""
    if key == keyboard.Key.insert:
        if not is_recording:
            start_recording()
    elif key == keyboard.Key.esc:
        logging.info("ESC pressed, exiting...")
        if is_recording:
            stop_recording_and_process()
        return False

def on_release(key):
    """Handle key release events"""
    if key == keyboard.Key.insert:
        if is_recording:
            stop_recording_and_process()

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    logging.info("Shutting down due to interrupt")
    if is_recording:
        stop_recording_and_process()
    sys.exit(0)

def main():
    """Main function"""
    # Set up signal handler for clean shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    logging.info("Starting key listener (pynput version)")
    logging.info("Hold INSERT key to record, release to transcribe")
    logging.info("Press ESC to exit")
    
    # Create and start the listener
    with keyboard.Listener(
        on_press=on_press,
        on_release=on_release) as listener:
        listener.join()

if __name__ == "__main__":
    main()