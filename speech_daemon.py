#!/usr/bin/env python3
"""
Persistent Speech-to-Text Daemon with Pre-loaded Models
- Keeps Whisper model loaded in memory (400MB RAM)
- Maintains warm Claude CLI session 
- Queue-based processing for sub-second performance
- Target: 0.5s processing vs 1.5s current approach
"""

import logging
import time
import threading
import queue
import os
import sys
import subprocess
import json
import signal
import glob
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/speech_daemon.log')
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

class SpeechDaemon:
    def __init__(self):
        self.model = None
        self.claude_session_warm = False
        self.processing_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.running = True
        
        # Performance tracking
        self.stats = {
            'processed': 0,
            'fast_path': 0,
            'claude_path': 0,
            'total_time': 0,
            'startup_time': 0
        }
        
        # Daemon state
        self.daemon_pid_file = '/tmp/speech_daemon.pid'
        
    def initialize_model(self):
        """Pre-load Whisper model at daemon startup"""
        logging.info("🔧 Initializing persistent Whisper base.en model...")
        start_time = time.time()
        
        self.model = WhisperModel("base.en", device="cpu", compute_type="int8")
        
        load_time = time.time() - start_time
        self.stats['startup_time'] = load_time
        logging.info(f"✅ Model permanently loaded in memory ({load_time:.2f}s, ~200MB)")
        
    def warm_claude_session(self):
        """Pre-warm Claude CLI for faster corrections"""
        logging.info("🔥 Pre-warming Claude CLI session...")
        try:
            cmd = ['claude', '-c', '-p', 'Speech daemon ready for context-aware corrections.']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                self.claude_session_warm = True
                logging.info("✅ Claude session pre-warmed")
            else:
                logging.warning("⚠️ Claude warm-up failed")
        except Exception as e:
            logging.warning(f"⚠️ Claude warm-up error: {e}")
    
    def startup_daemon(self):
        """Initialize daemon with all optimizations"""
        startup_start = time.time()
        logging.info("🚀 Starting Speech-to-Text Daemon...")
        
        # Pre-load everything in parallel
        import threading
        model_thread = threading.Thread(target=self.initialize_model)
        claude_thread = threading.Thread(target=self.warm_claude_session)
        
        model_thread.start()
        claude_thread.start()
        
        model_thread.join()
        claude_thread.join()
        
        startup_time = time.time() - startup_start
        logging.info(f"✅ Daemon fully initialized ({startup_time:.2f}s)")
        
        # Write PID file
        with open(self.daemon_pid_file, 'w') as f:
            f.write(str(os.getpid()))
        
        # Start background processor
        self.processor_thread = threading.Thread(target=self.background_processor, daemon=True)
        self.processor_thread.start()
        
        logging.info("🎯 Daemon ready for audio processing requests")
        
    def transcribe_with_confidence(self, audio):
        """Ultra-fast transcription with cached model"""
        start_time = time.time()
        
        segments, info = self.model.transcribe(
            audio, 
            language="en", 
            beam_size=5,
            best_of=2,
            temperature=0.0,
            vad_filter=False,
            word_timestamps=True
        )
        
        results = []
        confidences = []
        
        for segment in segments:
            text = segment.text.strip()
            if text:
                results.append(text)
                # Calculate confidence
                if hasattr(segment, 'words') and segment.words:
                    word_confidences = [word.probability for word in segment.words if hasattr(word, 'probability')]
                    avg_confidence = np.mean(word_confidences) if word_confidences else 0.5
                else:
                    avg_confidence = self.estimate_confidence_heuristic(text)
                confidences.append(avg_confidence)
        
        transcribe_time = time.time() - start_time
        overall_confidence = np.mean(confidences) if confidences else 0.0
        
        return ' '.join(results), overall_confidence, transcribe_time
    
    def estimate_confidence_heuristic(self, text):
        """Fast confidence estimation"""
        confidence = 1.0
        
        if len(text.split()) < 3:
            confidence -= 0.1
        
        words = text.lower().split()
        for word in words:
            if len(word) > 3 and not any(vowel in word for vowel in 'aeiou'):
                confidence -= 0.2
            if word in ['uh', 'um', 'er', 'ah']:
                confidence -= 0.1
        
        problematic_patterns = ['test thing', 'sting', 'dock her', 'coup da', 'sparrow low']
        for pattern in problematic_patterns:
            if pattern in text.lower():
                confidence -= 0.3
        
        return max(0.1, confidence)
    
    def correct_with_claude_fast(self, raw_transcript):
        """Fast Claude correction with warm session"""
        try:
            correction_prompt = f"""The speech-to-text system produced this raw transcript:

"{raw_transcript}"

Based on our current conversation context, please provide the corrected version that makes sense and is grammatically correct.

Please respond with ONLY the corrected transcript text, no explanations or quotes."""

            cmd = ['claude', '-c', '-p', correction_prompt]
            
            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            correction_time = time.time() - start_time
            
            if result.returncode == 0:
                corrected = result.stdout.strip()
                return corrected, correction_time
            else:
                logging.error(f"Claude correction failed: {result.stderr}")
                return raw_transcript, 0
                
        except Exception as e:
            logging.error(f"Claude correction error: {e}")
            return raw_transcript, 0
    
    def process_audio_request(self, audio_file):
        """Process single audio file with daemon optimizations"""
        request_start = time.time()
        
        # Load audio
        try:
            audio, samplerate = sf.read(audio_file)
            audio = audio.astype('float32')
            if len(audio.shape) > 1 and audio.shape[1] > 1:
                audio = np.mean(audio, axis=1)
        except Exception as e:
            logging.error(f"Failed to load audio: {e}")
            return None
        
        # Ultra-fast transcription (model already loaded)
        raw_transcript, confidence, transcribe_time = self.transcribe_with_confidence(audio)
        
        # Adaptive correction
        CONFIDENCE_THRESHOLD = 0.75
        
        if confidence >= CONFIDENCE_THRESHOLD:
            # Fast path
            final_transcript = raw_transcript
            correction_time = 0
            path = "FAST PATH"
            self.stats['fast_path'] += 1
        else:
            # Claude correction path
            final_transcript, correction_time = self.correct_with_claude_fast(raw_transcript)
            path = "CLAUDE PATH"
            self.stats['claude_path'] += 1
        
        total_time = time.time() - request_start
        self.stats['processed'] += 1
        self.stats['total_time'] += total_time
        
        result = {
            'raw': raw_transcript,
            'corrected': final_transcript,
            'confidence': confidence,
            'path': path,
            'transcribe_time': transcribe_time,
            'correction_time': correction_time,
            'total_time': total_time
        }
        
        logging.info(f"⚡ Processed: {total_time:.2f}s ({path}, confidence: {confidence:.2f})")
        return result
    
    def background_processor(self):
        """Background thread for processing audio requests"""
        while self.running:
            try:
                # Check for file-based requests (for client compatibility)
                self.check_file_requests()
                
                # Wait for queue-based audio processing request
                audio_file = self.processing_queue.get(timeout=1)
                if audio_file:
                    result = self.process_audio_request(audio_file)
                    if result:
                        self.result_queue.put(result)
                self.processing_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logging.error(f"Background processor error: {e}")
    
    def check_file_requests(self):
        """Check for file-based requests from clients"""
        request_files = glob.glob('/tmp/speech_request_*.json')
        
        for request_file in request_files:
            try:
                with open(request_file, 'r') as f:
                    request = json.load(f)
                
                audio_file = request['audio_file']
                response_file = request['response_file']
                
                # Process the request
                result = self.process_audio_request(audio_file)
                
                if result:
                    # Write response
                    with open(response_file, 'w') as f:
                        json.dump(result, f)
                    
                    logging.info(f"⚡ File request processed: {response_file}")
                
                # Cleanup request file
                os.remove(request_file)
                
            except Exception as e:
                logging.error(f"File request processing error: {e}")
                # Try to cleanup on error
                try:
                    os.remove(request_file)
                except:
                    pass
    
    def process_request(self, audio_file):
        """Public API: Submit audio for processing"""
        self.processing_queue.put(audio_file)
        
        # Get result (blocking)
        try:
            result = self.result_queue.get(timeout=30)
            return result
        except queue.Empty:
            logging.error("Processing timeout")
            return None
    
    def get_stats(self):
        """Get daemon performance statistics"""
        if self.stats['processed'] > 0:
            avg_time = self.stats['total_time'] / self.stats['processed']
            fast_ratio = self.stats['fast_path'] / self.stats['processed']
        else:
            avg_time = 0
            fast_ratio = 0
            
        return {
            'processed': self.stats['processed'],
            'fast_path': self.stats['fast_path'],
            'claude_path': self.stats['claude_path'],
            'fast_ratio': fast_ratio,
            'avg_time': avg_time,
            'startup_time': self.stats['startup_time']
        }
    
    def shutdown(self):
        """Graceful daemon shutdown"""
        logging.info("🛑 Shutting down speech daemon...")
        self.running = False
        
        # Cleanup PID file
        if os.path.exists(self.daemon_pid_file):
            os.remove(self.daemon_pid_file)
        
        # Print final stats
        stats = self.get_stats()
        logging.info(f"📊 Final stats: {stats['processed']} processed, {stats['avg_time']:.2f}s avg")

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    global daemon
    if daemon:
        daemon.shutdown()
    sys.exit(0)

def main():
    global daemon
    
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    print("🚀 Speech-to-Text Persistent Daemon")
    print("Memory cost: ~400MB for sub-second processing")
    print("Starting daemon...")
    
    # Create and start daemon
    daemon = SpeechDaemon()
    daemon.startup_daemon()
    
    print("✅ Daemon ready! Process audio files with:")
    print("   python3 -c \"import sys; sys.path.append('.'); from speech_daemon import daemon; print(daemon.process_request('/tmp/recorded_audio.wav'))\"")
    print("\nPress Ctrl+C to shutdown")
    
    # Keep daemon running
    try:
        while daemon.running:
            time.sleep(1)
    except KeyboardInterrupt:
        daemon.shutdown()

if __name__ == "__main__":
    main()