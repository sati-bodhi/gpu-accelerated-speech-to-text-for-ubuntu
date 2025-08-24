#!/usr/bin/env python3
"""
Optimized Speech-to-Text with Haiku Correction
- Uses Haiku model WITHOUT session continuity (-c flag)
- Prevents token accumulation issue
- Each correction is a fresh, minimal API call
"""

import sys
import os
import time
import logging
import subprocess
import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel
from typing import Tuple

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('/tmp/speech_to_text_optimized.log'),
        logging.StreamHandler()
    ]
)

# Configuration
CONFIDENCE_THRESHOLD = 0.75  # Above this, skip correction
MODEL_SIZE = "base.en"       # Good balance of speed/accuracy

def load_audio(file_path: str) -> np.ndarray:
    """Load and preprocess audio file"""
    try:
        audio, _ = sf.read(file_path)
        audio = audio.astype('float32')
        if len(audio.shape) > 1:
            audio = np.mean(audio, axis=1)
        return audio
    except Exception as e:
        logging.error(f"Failed to load audio: {e}")
        raise

def transcribe_audio(audio: np.ndarray, model: WhisperModel) -> Tuple[str, float]:
    """Transcribe audio and calculate confidence"""
    try:
        segments, _ = model.transcribe(
            audio,
            language="en",
            beam_size=1,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )
        
        all_segments = []
        total_confidence = 0
        segment_count = 0
        
        for segment in segments:
            text = segment.text.strip()
            if text:
                all_segments.append(text)
                # Use average probability as confidence
                total_confidence += segment.avg_logprob
                segment_count += 1
        
        raw_transcript = ' '.join(all_segments)
        
        # Calculate overall confidence
        if segment_count > 0:
            avg_logprob = total_confidence / segment_count
            # Convert log probability to 0-1 confidence
            confidence = min(1.0, max(0.0, 1.0 + (avg_logprob / 10)))
        else:
            confidence = 0.0
        
        return raw_transcript, confidence
        
    except Exception as e:
        logging.error(f"Transcription failed: {e}")
        raise

def correct_with_haiku(raw_transcript: str) -> Tuple[str, float]:
    """
    Correct transcript using Haiku WITHOUT session continuity
    This prevents token accumulation and ensures we use ONLY Haiku
    """
    try:
        # Build focused correction prompt
        correction_prompt = f"""Correct this speech-to-text transcript for grammar and context.

Raw transcript: "{raw_transcript}"

Rules:
1. Fix obvious speech recognition errors
2. Correct technical terms (e.g., "cuba" -> "CUDA", "haiku" -> "Haiku")
3. Maintain the speaker's intent
4. Output ONLY the corrected text, no explanations

Corrected transcript:"""

        # Call Claude CLI with Haiku model, NO -c flag
        cmd = [
            'claude',
            '-p',  # Print mode (no continue)
            '--model', 'claude-3-5-haiku-20241022',  # Explicitly use Haiku
            correction_prompt
        ]
        
        start_time = time.time()
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        correction_time = time.time() - start_time
        
        if result.returncode == 0:
            corrected = result.stdout.strip()
            # Remove quotes if present
            if corrected.startswith('"') and corrected.endswith('"'):
                corrected = corrected[1:-1]
            logging.info(f"✅ Haiku correction: {correction_time:.2f}s")
            return corrected, correction_time
        else:
            logging.error(f"Haiku failed: {result.stderr}")
            return raw_transcript, 0
            
    except subprocess.TimeoutExpired:
        logging.error("Haiku timed out")
        return raw_transcript, 0
    except Exception as e:
        logging.error(f"Haiku error: {e}")
        return raw_transcript, 0

def process_audio(audio_file: str) -> None:
    """Main processing pipeline"""
    
    start_time = time.time()
    
    # Load model (cached after first load)
    logging.info(f"🔧 Loading Whisper {MODEL_SIZE} model...")
    model_start = time.time()
    model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    model_time = time.time() - model_start
    if model_time < 0.1:
        logging.info(f"✅ Model already cached")
    else:
        logging.info(f"✅ Model loaded ({model_time:.2f}s)")
    
    # Load audio
    audio = load_audio(audio_file)
    duration = len(audio) / 16000  # Assuming 16kHz
    logging.info(f"Processing audio with duration {duration:.2f}s")
    
    # Transcribe
    transcribe_start = time.time()
    raw_transcript, confidence = transcribe_audio(audio, model)
    transcribe_time = time.time() - transcribe_start
    
    logging.info(f"📝 Raw: '{raw_transcript}' (confidence: {confidence:.2f})")
    
    # Decide on correction
    if confidence >= CONFIDENCE_THRESHOLD:
        final_transcript = raw_transcript
        correction_time = 0
        processing_path = "FAST PATH (high confidence)"
    else:
        final_transcript, correction_time = correct_with_haiku(raw_transcript)
        processing_path = "HAIKU CORRECTION (low confidence)"
    
    total_time = time.time() - start_time
    
    # Output results
    print("=" * 80)
    print("🎯 OPTIMIZED SPEECH-TO-TEXT (No Token Accumulation)")
    print("=" * 80)
    print(f"\n📝 RAW TRANSCRIPT ({MODEL_SIZE}):")
    print(f"   '{raw_transcript}'")
    print(f"   Confidence: {confidence:.2f}")
    
    if correction_time > 0:
        print(f"\n✨ CORRECTED TRANSCRIPT (Haiku):")
        print(f"   '{final_transcript}'")
    else:
        print(f"\n✅ HIGH CONFIDENCE - No correction needed")
    
    print(f"\n🎯 FINAL TRANSCRIPT ({processing_path}):")
    print(f"   '{final_transcript}'")
    
    print(f"\n📊 PERFORMANCE:")
    print(f"   Processing path: {processing_path}")
    print(f"   Confidence:      {confidence:.2f}")
    print(f"   Transcription:   {transcribe_time:.2f}s")
    print(f"   Correction:      {correction_time:.2f}s")
    print(f"   Total time:      {total_time:.2f}s")
    
    # Speed categories
    if total_time < 2:
        speed = "🚀 ULTRA FAST"
    elif total_time < 4:
        speed = "⚡ FAST"
    elif total_time < 8:
        speed = "🔄 MODERATE"
    else:
        speed = "🐢 SLOW"
    
    print(f"   Speed category:  {speed}")
    print("=" * 80)
    
    # Type the result
    if final_transcript:
        logging.info(f"⌨️ Typing: {final_transcript}")
        subprocess.run(['xdotool', 'type', '--', final_transcript])

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 speech_to_text_optimized.py <audio_file>")
        sys.exit(1)
    
    try:
        process_audio(sys.argv[1])
    except Exception as e:
        logging.error(f"Processing failed: {e}")
        print(f"❌ Error: {e}")
        sys.exit(1)