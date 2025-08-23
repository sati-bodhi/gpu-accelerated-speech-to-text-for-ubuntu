#!/usr/bin/env python3
"""
Confidence-based speech-to-text correction:
- High confidence: Type directly (fast ~1s)
- Low confidence: Send to Claude for correction (~8s)
- Adaptive: Most transcripts are high confidence, average ~2-3s
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
        logging.FileHandler('/tmp/speech_to_text_confidence.log')
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

# Global cached model
cached_model = None

def get_cached_model():
    """Get or initialize cached Whisper model"""
    global cached_model
    if cached_model is None:
        logging.info("🔧 Loading Whisper base.en model (one-time cache)...")
        start_time = time.time()
        cached_model = WhisperModel("base.en", device="cpu", compute_type="int8")
        load_time = time.time() - start_time
        logging.info(f"✅ Model cached ({load_time:.2f}s)")
    else:
        logging.info("⚡ Using cached model")
    return cached_model

def transcribe_with_confidence(audio):
    """Transcribe audio and return segments with confidence scores"""
    model = get_cached_model()
    
    start_time = time.time()
    segments, info = model.transcribe(
        audio, 
        language="en", 
        beam_size=5,  # Higher beam size for better confidence estimates
        best_of=2,    # Multiple passes for confidence
        temperature=0.0,  # Deterministic for consistent confidence
        vad_filter=False,
        word_timestamps=True  # Get word-level confidence
    )
    
    results = []
    confidences = []
    
    for segment in segments:
        text = segment.text.strip()
        if text:
            results.append(text)
            # Calculate average confidence for this segment
            if hasattr(segment, 'words') and segment.words:
                word_confidences = [word.probability for word in segment.words if hasattr(word, 'probability')]
                avg_confidence = np.mean(word_confidences) if word_confidences else 0.5
            else:
                # Fallback: estimate confidence based on recognition patterns
                avg_confidence = estimate_confidence_heuristic(text)
            
            confidences.append(avg_confidence)
            logging.info(f"📝 '{text}' (confidence: {avg_confidence:.2f})")
    
    transcribe_time = time.time() - start_time
    overall_confidence = np.mean(confidences) if confidences else 0.0
    
    logging.info(f"⚡ Transcription: {transcribe_time:.2f}s, overall confidence: {overall_confidence:.2f}")
    
    return results, overall_confidence

def estimate_confidence_heuristic(text):
    """Estimate confidence based on common error patterns"""
    confidence = 1.0
    
    # Lower confidence indicators
    if len(text.split()) < 3:
        confidence -= 0.1  # Very short phrases often misheard
    
    # Check for garbled words (multiple consonants, no vowels)
    words = text.lower().split()
    for word in words:
        if len(word) > 3 and not any(vowel in word for vowel in 'aeiou'):
            confidence -= 0.2  # Likely garbled
        if word in ['uh', 'um', 'er', 'ah']:
            confidence -= 0.1  # Filler words suggest unclear audio
    
    # Check for known problematic patterns
    problematic_patterns = ['test thing', 'sting', 'dock her', 'coup da', 'sparrow low']
    for pattern in problematic_patterns:
        if pattern in text.lower():
            confidence -= 0.3
    
    return max(0.1, confidence)  # Minimum confidence of 0.1

def correct_with_claude_cli(raw_transcript):
    """Claude CLI correction (for low confidence transcripts)"""
    try:
        logging.info("🤖 Low confidence detected - sending to Claude for correction...")
        
        correction_prompt = f"""The speech-to-text system produced this raw transcript:

"{raw_transcript}"

Based on our current conversation context, please provide the corrected version that makes sense and is grammatically correct. 

Please respond with ONLY the corrected transcript text, no explanations or quotes."""

        cmd = ['claude', '-c', '-p', correction_prompt]
        
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        correction_time = time.time() - start_time
        
        if result.returncode == 0:
            corrected = result.stdout.strip()
            logging.info(f"🤖 Claude correction: {correction_time:.2f}s")
            return corrected, correction_time
        else:
            logging.error(f"Claude CLI failed: {result.stderr}")
            return raw_transcript, 0
            
    except subprocess.TimeoutExpired:
        logging.error("Claude CLI timed out")
        return raw_transcript, 0
    except Exception as e:
        logging.error(f"Claude CLI error: {e}")
        return raw_transcript, 0

def load_audio(file_path):
    """Load and preprocess audio file"""
    if not os.path.exists(file_path):
        logging.error(f"Audio file not found: {file_path}")
        return None
    
    try:
        audio, samplerate = sf.read(file_path)
        audio = audio.astype('float32')
        
        if len(audio.shape) > 1 and audio.shape[1] > 1:
            audio = np.mean(audio, axis=1)
        
        return audio
        
    except Exception as e:
        logging.error(f"Failed to read audio: {e}")
        return None

def type_text(text):
    """Type text using pyautogui"""
    try:
        logging.info(f"⌨️ Typing: {text}")
        pyautogui.typewrite(text + ' ')
    except Exception as e:
        logging.error(f"Failed to type: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python speech_to_text_confidence.py <audio_file>")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    session_start = time.time()
    
    print("=" * 80)
    print("🎯 CONFIDENCE-BASED ADAPTIVE CORRECTION")
    print("=" * 80)
    
    # Load audio
    audio = load_audio(audio_file)
    if audio is None:
        sys.exit(1)
    
    # Transcribe with confidence scoring
    segments, confidence = transcribe_with_confidence(audio)
    raw_transcript = ' '.join(segments)
    
    print(f"\n📝 RAW TRANSCRIPT (base.en):")
    print(f"   '{raw_transcript}'")
    print(f"   Confidence: {confidence:.2f}")
    
    # Adaptive correction based on confidence
    CONFIDENCE_THRESHOLD = 0.75  # Adjustable threshold
    
    if confidence >= CONFIDENCE_THRESHOLD:
        # High confidence - type directly
        print(f"\n✅ HIGH CONFIDENCE ({confidence:.2f} ≥ {CONFIDENCE_THRESHOLD}) - Using direct transcript")
        final_transcript = raw_transcript
        correction_time = 0
        processing_path = "FAST PATH"
    else:
        # Low confidence - send to Claude
        print(f"\n⚠️ LOW CONFIDENCE ({confidence:.2f} < {CONFIDENCE_THRESHOLD}) - Sending to Claude")
        final_transcript, correction_time = correct_with_claude_cli(raw_transcript)
        processing_path = "CLAUDE CORRECTION"
    
    total_time = time.time() - session_start
    
    print(f"\n🎯 FINAL TRANSCRIPT ({processing_path}):")
    print(f"   '{final_transcript}'")
    
    print(f"\n📊 PERFORMANCE:")
    print(f"   Processing path: {processing_path}")
    print(f"   Confidence:      {confidence:.2f}")
    print(f"   Correction time: {correction_time:.2f}s")
    print(f"   Total time:      {total_time:.2f}s")
    print(f"   Speed category:  {'🚀 FAST' if total_time < 3 else '🐌 SLOW'}")
    
    # Type result
    type_text(final_transcript)
    
    print("=" * 80)

if __name__ == "__main__":
    main()