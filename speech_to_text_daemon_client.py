#!/usr/bin/env python3
"""
Client for the persistent speech daemon.
Ultra-fast processing using pre-loaded models.
"""

import sys
import os
import socket
import json
import time
import logging
import subprocess

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/speech_client.log')
    ]
)

try:
    import pyautogui
except ImportError as e:
    print(f"Error: Required library not found: {e}")
    sys.exit(1)

def check_daemon_running():
    """Check if speech daemon is running"""
    pid_file = '/tmp/speech_daemon.pid'
    if os.path.exists(pid_file):
        try:
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())
            # Check if process is actually running
            os.kill(pid, 0)  # This throws if process doesn't exist
            return True
        except (OSError, ValueError):
            # PID file exists but process is dead
            os.remove(pid_file)
            return False
    return False

def start_daemon_if_needed():
    """Start daemon if not already running"""
    if not check_daemon_running():
        logging.info("🚀 Starting speech daemon...")
        # Start daemon in background
        subprocess.Popen([
            sys.executable, 
            os.path.join(os.path.dirname(__file__), 'speech_daemon.py')
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Wait for daemon to initialize
        max_wait = 30
        for i in range(max_wait):
            if check_daemon_running():
                logging.info("✅ Daemon started and ready")
                return True
            time.sleep(1)
        
        logging.error("❌ Failed to start daemon")
        return False
    else:
        logging.info("⚡ Using existing daemon")
        return True

def process_with_daemon(audio_file):
    """Process audio file using persistent daemon"""
    if not start_daemon_if_needed():
        logging.error("Cannot start daemon - falling back to direct processing")
        return process_without_daemon(audio_file)
    
    try:
        # For this prototype, use file-based communication
        # In production, would use proper IPC (sockets, pipes, etc.)
        
        request_file = f'/tmp/speech_request_{int(time.time() * 1000)}.json'
        response_file = f'/tmp/speech_response_{int(time.time() * 1000)}.json'
        
        # Create request
        request = {
            'audio_file': audio_file,
            'response_file': response_file,
            'timestamp': time.time()
        }
        
        # Write request
        with open(request_file, 'w') as f:
            json.dump(request, f)
        
        # Signal daemon (for now, daemon polls for requests)
        # Wait for response
        max_wait = 60
        for i in range(max_wait * 10):  # Check every 100ms
            if os.path.exists(response_file):
                with open(response_file, 'r') as f:
                    response = json.load(f)
                
                # Cleanup
                os.remove(request_file)
                os.remove(response_file)
                
                return response
            
            time.sleep(0.1)
        
        logging.error("Daemon response timeout")
        return None
        
    except Exception as e:
        logging.error(f"Daemon communication error: {e}")
        return process_without_daemon(audio_file)

def process_without_daemon(audio_file):
    """Fallback: direct processing without daemon"""
    logging.warning("⚠️ Using fallback processing (slower)")
    
    # This is essentially what the current confidence-based script does
    # but without the optimizations
    
    try:
        import numpy as np
        import soundfile as sf
        from faster_whisper import WhisperModel
        
        # Load model (slow)
        model = WhisperModel("base.en", device="cpu", compute_type="int8")
        
        # Load audio
        audio, _ = sf.read(audio_file)
        audio = audio.astype('float32')
        if len(audio.shape) > 1:
            audio = np.mean(audio, axis=1)
        
        # Transcribe
        segments, _ = model.transcribe(audio, language="en", beam_size=1)
        raw_transcript = ' '.join(seg.text.strip() for seg in segments if seg.text.strip())
        
        return {
            'raw': raw_transcript,
            'corrected': raw_transcript,
            'confidence': 0.8,  # Assume decent
            'path': 'FALLBACK',
            'total_time': 2.0  # Estimate
        }
        
    except Exception as e:
        logging.error(f"Fallback processing failed: {e}")
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
        print("Usage: python speech_to_text_daemon_client.py <audio_file>")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    
    print("=" * 80)
    print("⚡ PERSISTENT DAEMON CLIENT")
    print("=" * 80)
    
    # Process via daemon
    result = process_with_daemon(audio_file)
    
    if result:
        print(f"\n📝 RAW TRANSCRIPT:")
        print(f"   '{result['raw']}'")
        print(f"   Confidence: {result.get('confidence', 0):.2f}")
        
        print(f"\n✨ FINAL TRANSCRIPT ({result['path']}):")
        print(f"   '{result['corrected']}'")
        
        print(f"\n📊 DAEMON PERFORMANCE:")
        print(f"   Total time:  {result.get('total_time', 0):.2f}s")
        print(f"   Speed:       {'🚀 ULTRA FAST' if result.get('total_time', 0) < 1 else '🚀 FAST' if result.get('total_time', 0) < 3 else '🐌 SLOW'}")
        
        # Type result
        type_text(result['corrected'])
        
    else:
        print("❌ Processing failed")
    
    print("=" * 80)

if __name__ == "__main__":
    main()