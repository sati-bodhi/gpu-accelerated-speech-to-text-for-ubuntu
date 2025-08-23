#!/usr/bin/env python3
"""
GPU-accelerated speech-to-text processor using Faster Whisper medium model.
Falls back to CPU if GPU is not available.
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
    """Transcribe audio using Whisper with GPU acceleration."""
    try:
        # Try GPU first, fall back to CPU if needed
        device = "cuda"
        compute_type = "float16"
        model_size = "medium.en"  # Better accuracy
        
        try:
            logging.info(f"Loading Whisper {model_size} model on GPU...")
            start_time = time.time()
            model = WhisperModel(model_size, device=device, compute_type=compute_type)
            logging.info(f"Model loaded in {time.time() - start_time:.2f}s")
        except Exception as gpu_error:
            logging.warning(f"GPU initialization failed: {gpu_error}")
            logging.info("Falling back to CPU with smaller model...")
            device = "cpu"
            compute_type = "int8"
            model_size = "base.en"  # Use base on CPU for better speed
            model = WhisperModel(model_size, device=device, compute_type=compute_type)
            logging.info(f"Using {model_size} on CPU")
        
        logging.info("Starting transcription...")
        start_time = time.time()
        segments, info = model.transcribe(
            audio, 
            language="en", 
            beam_size=5,  # Better accuracy
            best_of=5,    # Better accuracy
            temperature=0,  # More deterministic
            vad_filter=True,  # Re-enable with GPU
            vad_parameters=dict(
                threshold=0.5,
                min_silence_duration_ms=500,
                min_speech_duration_ms=250
            )
        )
        
        # Process segments
        results = []
        for seg in segments:
            text = seg.text.strip()
            if text:
                results.append(text)
                logging.info(f"Recognized: {text}")
        
        transcribe_time = time.time() - start_time
        logging.info(f"Transcription completed in {transcribe_time:.2f}s: {len(results)} segments")
        logging.info(f"Using {device.upper()} with {model_size} model")
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
        print("Usage: python speech_to_text_gpu.py <audio_file>")
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