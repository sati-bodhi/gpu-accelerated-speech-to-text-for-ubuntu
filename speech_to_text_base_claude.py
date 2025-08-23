#!/usr/bin/env python3
"""
Speech-to-text with base.en model + Claude CLI context-aware correction.
Combines better base accuracy with intelligent correction.
"""

import logging
import sys
import os
import subprocess
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

def correct_transcript_with_claude_cli(raw_transcript):
    """Use Claude CLI with session context for generic correction."""
    try:
        logging.info("Sending transcript to Claude CLI for context-aware correction...")
        
        correction_prompt = f"""The speech-to-text system produced this raw transcript:

"{raw_transcript}"

Based on our current conversation context, please provide the corrected version that makes sense and is grammatically correct. Consider:
- Common speech recognition errors (homophones, missing words, word boundaries)  
- Technical terminology that might have been misrecognized
- The conversational context of what we've been discussing
- Proper grammar and sentence structure

Please respond with ONLY the corrected transcript text, no explanations or quotes."""

        cmd = ['claude', '-c', '-p', correction_prompt]
        
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        correction_time = time.time() - start_time
        
        if result.returncode == 0:
            corrected = result.stdout.strip()
            logging.info(f"Claude CLI correction completed in {correction_time:.2f}s")
            return corrected
        else:
            logging.error(f"Claude CLI failed: {result.stderr}")
            return raw_transcript
            
    except subprocess.TimeoutExpired:
        logging.error("Claude CLI correction timed out")
        return raw_transcript
    except Exception as e:
        logging.error(f"Claude CLI correction failed: {e}")
        return raw_transcript

def transcribe_audio(audio):
    """Transcribe using base.en for better accuracy"""
    try:
        logging.info("Loading Whisper base.en model (better accuracy)...")
        start_time = time.time()
        model = WhisperModel("base.en", device="cpu", compute_type="int8")
        load_time = time.time() - start_time
        logging.info(f"Model loaded in {load_time:.2f} seconds")
        
        logging.info("Starting transcription...")
        transcribe_start = time.time()
        segments, _ = model.transcribe(
            audio, 
            language="en", 
            beam_size=1, 
            vad_filter=False
        )
        
        results = []
        for seg in segments:
            text = seg.text.strip()
            if text:
                results.append(text)
        
        transcribe_time = time.time() - transcribe_start
        logging.info(f"Transcription completed in {transcribe_time:.2f} seconds: {len(results)} segments")
        return results
        
    except Exception as e:
        logging.error(f"Transcription failed: {e}")
        sys.exit(1)

def load_audio(file_path):
    """Load and preprocess audio file"""
    if not os.path.exists(file_path):
        logging.error(f"Audio file not found: {file_path}")
        sys.exit(1)
    
    try:
        audio, samplerate = sf.read(file_path)
        audio = audio.astype('float32')
        
        if len(audio.shape) > 1 and audio.shape[1] > 1:
            audio = np.mean(audio, axis=1)
        
        return audio
        
    except Exception as e:
        logging.error(f"Failed to read audio file {file_path}: {e}")
        sys.exit(1)

def type_text(text):
    """Type text using pyautogui"""
    try:
        logging.info(f"Typing: {text}")
        pyautogui.typewrite(text + ' ')
    except Exception as e:
        logging.error(f"Failed to type text: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python speech_to_text_base_claude.py <audio_file>")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    
    print("=" * 80)
    print("BASE.EN MODEL + CLAUDE CLI CONTEXT-AWARE CORRECTION")
    print("=" * 80)
    
    # Process audio with base.en
    audio = load_audio(audio_file)
    segments = transcribe_audio(audio)
    raw_transcript = ' '.join(segments)
    
    print(f"\n📝 RAW TRANSCRIPT (base.en):")
    print(f"   '{raw_transcript}'")
    print(f"   Length: {len(raw_transcript)} characters")
    
    # Apply Claude CLI correction
    print(f"\n⏳ Applying Claude CLI context-aware correction...")
    print(f"   (Using session context automatically)")
    
    start_correction = time.time()
    corrected_transcript = correct_transcript_with_claude_cli(raw_transcript)
    correction_time = time.time() - start_correction
    
    print(f"\n✨ CORRECTED TRANSCRIPT (base.en + Claude CLI):")
    print(f"   '{corrected_transcript}'")
    print(f"   Length: {len(corrected_transcript)} characters")
    
    print(f"\n📊 ANALYSIS:")
    print(f"   Model:      base.en (better initial accuracy)")
    print(f"   Original:   '{raw_transcript}'")
    print(f"   Corrected:  '{corrected_transcript}'")
    print(f"   Same text:  {'Yes' if raw_transcript == corrected_transcript else 'No'}")
    print(f"   Char diff:  {len(corrected_transcript) - len(raw_transcript):+d}")
    print(f"   Correction: {correction_time:.2f} seconds")
    
    if raw_transcript != corrected_transcript:
        print(f"   Status:     ✅ CORRECTION APPLIED")
    else:
        print(f"   Status:     ➖ NO CORRECTION NEEDED")
    
    # Type the corrected version
    print(f"\n🎯 Typing corrected version...")
    type_text(corrected_transcript)
    
    print("=" * 80)

if __name__ == "__main__":
    main()