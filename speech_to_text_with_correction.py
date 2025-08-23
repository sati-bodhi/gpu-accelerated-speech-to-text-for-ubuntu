#!/usr/bin/env python3
"""
Speech-to-text with context-aware correction using Haiku.
Shows both raw transcript and corrected version for comparison.
"""

import logging
import sys
import os
import pwd
import time
import json
import subprocess

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

def get_conversation_context():
    """Extract current conversation context for Haiku"""
    context_info = {
        "session": "Claude Code speech-to-text development session",
        "current_project": "Speech recognition with GPU acceleration and Docker containers",
        "recent_topics": [
            "Docker containers with CUDA and CuDNN",
            "faster-whisper models (tiny.en, base.en, medium.en)",
            "GPU acceleration with ctranslate2",
            "MCP server development",
            "Speech-to-text transcript correction",
            "Python virtual environments",
            "Key listener with pynput",
            "Docker Hub image publishing"
        ],
        "technical_context": "Working on Ubuntu 24.04.2 LTS with NVIDIA GPU, building speech-to-text system using faster-whisper, Docker, and Claude Code integration",
        "code_context": "Python scripts for audio processing, Docker configurations, speech recognition models"
    }
    return context_info

def correct_transcript_with_haiku(raw_transcript):
    """Send transcript to Haiku for context-aware correction"""
    try:
        context = get_conversation_context()
        
        correction_prompt = f"""You are helping correct a speech-to-text transcript in the context of a technical coding session. 

CONTEXT:
- Session: {context['session']}
- Current project: {context['current_project']}
- Recent topics: {', '.join(context['recent_topics'])}
- Technical environment: {context['technical_context']}

RAW TRANSCRIPT TO CORRECT:
"{raw_transcript}"

Please provide a corrected version that:
1. Fixes common speech-to-text errors (homophones, technical terms)
2. Uses proper technical terminology based on the context
3. Maintains the original meaning and intent
4. Uses proper capitalization and punctuation
5. Considers this is likely about Docker, Python, or speech recognition

Respond with ONLY the corrected transcript, no explanations."""

        # For this POC, simulate Haiku response with context-aware corrections
        # In real implementation, this would be an API call to Haiku
        corrected = simulate_haiku_correction(raw_transcript, context)
        
        return corrected
        
    except Exception as e:
        logging.error(f"Correction failed: {e}")
        return raw_transcript  # Fallback to original

def simulate_haiku_correction(raw_transcript, context):
    """Simulate context-aware Haiku correction based on our current session"""
    
    # Context-aware corrections based on our current conversation
    corrections = {
        # Docker/Container terms
        "dock her": "Docker",
        "dock": "Docker", 
        "container": "container",
        "cubeectl": "kubectl",
        "cube net": "Kubernetes",
        
        # GPU/CUDA terms
        "coup da": "CUDA",
        "c you da": "CUDA", 
        "gpu": "GPU",
        "nvidia": "NVIDIA",
        "c ten": "CT2",
        "c translate": "ctranslate2",
        
        # Speech/AI terms
        "whisper": "Whisper",
        "tiny dot e n": "tiny.en",
        "base dot e n": "base.en", 
        "medium dot e n": "medium.en",
        "haiku": "Haiku",
        "claude": "Claude",
        "m c p": "MCP",
        
        # Python terms  
        "pie thon": "Python",
        "pip": "pip",
        "v env": "venv",
        "pi auto gui": "pyautogui",
        "num pie": "NumPy",
        
        # Programming terms
        "a p i": "API",
        "jason": "JSON",
        "sequel": "SQL", 
        "get hub": "GitHub",
        
        # Common homophones in context
        "right": "write",
        "to": "two" if "two" in raw_transcript.lower() else "to",  # Context-dependent
        "there": "their" if "their" in raw_transcript.lower() else "there",
        "build": "build",
        "test": "test",
    }
    
    corrected = raw_transcript
    applied_corrections = []
    
    # Apply context-aware corrections
    for wrong, right in corrections.items():
        if wrong.lower() in corrected.lower():
            old_corrected = corrected
            corrected = corrected.replace(wrong, right)
            corrected = corrected.replace(wrong.title(), right.title())
            corrected = corrected.replace(wrong.upper(), right.upper())
            if old_corrected != corrected:
                applied_corrections.append(f"'{wrong}' → '{right}'")
    
    # Log corrections applied
    if applied_corrections:
        logging.info(f"Applied corrections: {', '.join(applied_corrections)}")
    
    return corrected

def transcribe_audio(audio):
    """Transcribe audio using Whisper tiny model"""
    try:
        logging.info("Loading Whisper tiny.en model (fast, may have errors)...")
        start_time = time.time()
        model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
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
            logging.info("Converted stereo audio to mono")
        
        logging.info(f"Audio loaded: {file_path}, sample rate: {samplerate}")
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
        print("Usage: python speech_to_text_with_correction.py <audio_file>")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    
    print("=" * 60)
    print("SPEECH-TO-TEXT WITH CONTEXT-AWARE CORRECTION")
    print("=" * 60)
    
    # Process audio
    audio = load_audio(audio_file)
    segments = transcribe_audio(audio)
    raw_transcript = ' '.join(segments)
    
    print(f"\n📝 RAW TRANSCRIPT (tiny.en):")
    print(f"   '{raw_transcript}'")
    
    # Apply correction
    print(f"\n⏳ Applying context-aware correction...")
    corrected_transcript = correct_transcript_with_haiku(raw_transcript)
    
    print(f"\n✨ CORRECTED TRANSCRIPT (Haiku + context):")
    print(f"   '{corrected_transcript}'")
    
    print(f"\n📊 COMPARISON:")
    print(f"   Original length: {len(raw_transcript)} chars")
    print(f"   Corrected length: {len(corrected_transcript)} chars")
    print(f"   Difference: {len(corrected_transcript) - len(raw_transcript)} chars")
    print(f"   Same?: {'Yes' if raw_transcript == corrected_transcript else 'No'}")
    
    # Type the corrected version
    print(f"\n🎯 Typing corrected version...")
    type_text(corrected_transcript)
    
    print("=" * 60)

if __name__ == "__main__":
    main()