#!/usr/bin/env python3
"""
Speech-to-text processor using Faster Whisper medium.en model for better accuracy.

The script expects an audio file (e.g. /tmp/recorded_audio.wav) as an argument.

Usage: python3 speech_to_text_medium.py <audio_file>

Tested on Ubuntu 24.04.2 LTS

The script is intended to be run using your Python virtual environment (see key_listener.py).
"""

import logging
import sys
import os
import pwd
import time


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/speech_to_text.log')
    ]
)

try:
    import numpy as np
    import pyautogui
    import soundfile as sf
    from faster_whisper import WhisperModel
except ImportError as e:
    print(f"Error: Required library not found: {e}")
    print("Install in your venv with: pip install numpy pyautogui soundfile faster-whisper")
    sys.exit(1)

def log_user_info():
    """Log current user information."""
    try:
        uid = os.geteuid()
        user = pwd.getpwuid(uid).pw_name
        logging.info(f"Running as user: {os.getlogin()}")
        logging.info(f"Effective user: {user} (UID: {uid})")
    except Exception as e:
        logging.warning(f"Could not determine user info: {e}")

def load_audio(file_path):
    """Load and preprocess audio file."""
    if not os.path.exists(file_path):
        logging.error(f"Audio file not found: {file_path}")
        sys.exit(1)
    
    try:
        audio, samplerate = sf.read(file_path)
        audio = audio.astype('float32')
        
        # Convert stereo to mono if necessary
        if len(audio.shape) > 1 and audio.shape[1] > 1:
            audio = np.mean(audio, axis=1)
            logging.info("Converted stereo audio to mono")
        
        logging.info(f"Audio loaded: {file_path}, sample rate: {samplerate}")
        return audio
        
    except Exception as e:
        logging.error(f"Failed to read audio file {file_path}: {e}")
        sys.exit(1)

def transcribe_audio(audio):
    """Transcribe audio using Whisper medium model."""
    try:
        logging.info("Loading Whisper medium.en model (this may take longer than tiny.en)...")
        start_load = time.time()
        model = WhisperModel("medium.en", device="cpu", compute_type="int8")
        load_time = time.time() - start_load
        logging.info(f"Model loaded in {load_time:.2f} seconds")
        
        logging.info("Starting transcription...")
        start_transcribe = time.time()
        segments, _ = model.transcribe(
            audio, 
            language="en", 
            beam_size=1, 
            vad_filter=False  # Disabled VAD due to low microphone volume issues
        )
        
        # Process segments
        results = []
        for seg in segments:
            text = seg.text.strip()
            if text:
                results.append(text)
                logging.info(f"Recognized: {text}")
        
        transcribe_time = time.time() - start_transcribe
        logging.info(f"Transcription completed in {transcribe_time:.2f} seconds: {len(results)} segments")
        return results
        
    except Exception as e:
        logging.error(f"Transcription failed: {e}")
        sys.exit(1)

def type_text(text):
    """Type text using pyautogui."""
    try:
        logging.info(f"Typing: {text}")
        pyautogui.typewrite(text + ' ')
    except Exception as e:
        logging.error(f"Failed to type text: {e}")

def main():
    """Main function."""
    # Check arguments
    if len(sys.argv) < 2:
        print("Usage: python speech_to_text_medium.py <audio_file>")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    
    # Log user info
    log_user_info()
    
    # Process audio
    logging.info(f"Processing audio file: {audio_file}")
    
    # Load audio
    audio = load_audio(audio_file)
    
    # Transcribe
    segments = transcribe_audio(audio)
    
    # Type results
    for segment in segments:
        type_text(segment)
    
    logging.info("Processing completed")

if __name__ == "__main__":
    main()