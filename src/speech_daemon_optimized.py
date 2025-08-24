#!/usr/bin/env python3
"""
Persistent Speech-to-Text Daemon with GPU Optimization
Keeps Whisper model loaded in memory for instant transcription
"""

import os
import sys
import time
import json
import logging
import threading
from pathlib import Path
import signal

# Set up CUDA environment before imports
def setup_cuda_env():
    """Set up CUDA environment variables."""
    try:
        venv_path = os.path.dirname(os.path.dirname(sys.executable))
        cudnn_lib_path = os.path.join(venv_path, 'lib/python3.10/site-packages/nvidia/cudnn/lib')
        cublas_lib_path = os.path.join(venv_path, 'lib/python3.10/site-packages/nvidia/cublas/lib')
        
        current_path = os.environ.get('LD_LIBRARY_PATH', '')
        new_paths = [cudnn_lib_path, cublas_lib_path]
        if current_path:
            new_paths.append(current_path)
        os.environ['LD_LIBRARY_PATH'] = ':'.join(new_paths)
        return True
    except Exception as e:
        print(f"CUDA setup failed: {e}")
        return False

setup_cuda_env()

try:
    import numpy as np
    import pyautogui
    import soundfile as sf
    from faster_whisper import WhisperModel
except ImportError as e:
    print(f"Required library missing: {e}")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/speech_daemon.log')
    ]
)

class PersistentSpeechService:
    """High-performance persistent speech-to-text service."""
    
    def __init__(self):
        self.model = None
        self.device = None
        self.model_size = None
        self.is_ready = False
        self.processing = False
        self.job_queue = []
        self.lock = threading.Lock()
        
        # Service control paths
        self.request_dir = Path("/tmp/speech_requests")
        self.response_dir = Path("/tmp/speech_responses")
        self.status_file = Path("/tmp/speech_daemon_status.json")
        
        self.setup_directories()
        self.load_model()
        self.update_status()
    
    def setup_directories(self):
        """Create necessary directories for IPC."""
        self.request_dir.mkdir(exist_ok=True)
        self.response_dir.mkdir(exist_ok=True)
        logging.info(f"Service directories ready: {self.request_dir}, {self.response_dir}")
    
    def load_model(self):
        """Load and cache Whisper model permanently."""
        try:
            logging.info("Loading persistent Whisper model...")
            start_time = time.time()
            
            # Try GPU first
            try:
                self.device = "cuda"
                self.model_size = "large-v3"
                self.model = WhisperModel(
                    self.model_size, 
                    device=self.device, 
                    compute_type="float16"
                )
                logging.info(f"GPU model loaded in {time.time() - start_time:.2f}s")
            except Exception as gpu_error:
                logging.warning(f"GPU failed: {gpu_error}, using CPU")
                self.device = "cpu"
                self.model_size = "large-v3"
                self.model = WhisperModel(
                    self.model_size, 
                    device=self.device, 
                    compute_type="int8"
                )
                logging.info(f"CPU model loaded in {time.time() - start_time:.2f}s")
            
            self.is_ready = True
            logging.info(f"Persistent service ready on {self.device.upper()}")
            
        except Exception as e:
            logging.error(f"Model loading failed: {e}")
            sys.exit(1)
    
    def update_status(self):
        """Update daemon status file."""
        status = {
            "ready": self.is_ready,
            "device": self.device,
            "model_size": self.model_size,
            "processing": self.processing,
            "timestamp": time.time(),
            "pid": os.getpid()
        }
        
        try:
            with open(self.status_file, 'w') as f:
                json.dump(status, f)
        except Exception as e:
            logging.warning(f"Failed to update status: {e}")
    
    def check_audio_content(self, audio, sample_rate):
        """Fast pre-filter for empty audio."""
        try:
            duration = len(audio) / sample_rate
            if duration < 0.2:  # Too short
                return False
                
            rms_level = np.sqrt(np.mean(audio**2))
            if rms_level < 0.001:  # Too quiet
                return False
                
            return True
            
        except Exception:
            return True  # Process anyway if check fails
    
    def transcribe_audio(self, audio_file):
        """Transcribe audio using persistent model."""
        with self.lock:
            self.processing = True
            self.update_status()
        
        try:
            # Load audio
            start_time = time.time()
            audio, sample_rate = sf.read(audio_file)
            audio = audio.astype('float32')
            
            # Convert stereo to mono
            if len(audio.shape) > 1:
                audio = np.mean(audio, axis=1)
            
            load_time = time.time() - start_time
            logging.info(f"Audio loaded in {load_time:.3f}s")
            
            # Pre-filter empty audio
            if not self.check_audio_content(audio, sample_rate):
                logging.info("Skipping empty/silent audio")
                return []
            
            # Transcribe with persistent model (no loading overhead!)
            start_time = time.time()
            segments, info = self.model.transcribe(
                audio,
                language="en",
                beam_size=5,
                best_of=5,
                temperature=0,
                vad_filter=True,
                vad_parameters=dict(
                    threshold=0.5,
                    min_silence_duration_ms=500,
                    min_speech_duration_ms=250
                )
            )
            
            # Extract results
            results = []
            for seg in segments:
                text = seg.text.strip()
                if text:
                    results.append(text)
            
            transcribe_time = time.time() - start_time
            logging.info(f"Transcription: {transcribe_time:.3f}s, {len(results)} segments")
            logging.info(f"PERSISTENT {self.device.upper()} - zero loading overhead!")
            
            return results
            
        except Exception as e:
            logging.error(f"Transcription failed: {e}")
            return []
        finally:
            with self.lock:
                self.processing = False
                self.update_status()
    
    def process_request(self, request_file):
        """Process a single transcription request."""
        try:
            # Read request
            with open(request_file, 'r') as f:
                request = json.load(f)
            
            audio_file = request.get('audio_file')
            request_id = request.get('id')
            
            logging.info(f"Processing request {request_id}: {audio_file}")
            
            # Transcribe
            results = self.transcribe_audio(audio_file)
            
            # Write response
            response = {
                'id': request_id,
                'results': results,
                'timestamp': time.time(),
                'device': self.device
            }
            
            response_file = self.response_dir / f"{request_id}.json"
            with open(response_file, 'w') as f:
                json.dump(response, f)
            
            # Auto-type results
            for text in results:
                try:
                    pyautogui.typewrite(text + ' ')
                    logging.info(f"Typed: {text}")
                except Exception as e:
                    logging.warning(f"Typing failed: {e}")
            
            # Clean up
            request_file.unlink()
            logging.info(f"Request {request_id} completed")
            
        except Exception as e:
            logging.error(f"Request processing failed: {e}")
    
    def monitor_requests(self):
        """Monitor for incoming requests."""
        logging.info("Starting request monitor...")
        
        while self.is_ready:
            try:
                # Check for new requests
                request_files = list(self.request_dir.glob("*.json"))
                
                for request_file in request_files:
                    self.process_request(request_file)
                
                # Brief pause
                time.sleep(0.1)
                
            except KeyboardInterrupt:
                logging.info("Received shutdown signal")
                break
            except Exception as e:
                logging.error(f"Monitor error: {e}")
                time.sleep(1)
    
    def cleanup(self):
        """Clean up daemon resources."""
        logging.info("Cleaning up daemon...")
        
        # Remove status file
        if self.status_file.exists():
            self.status_file.unlink()
        
        # Clear pending requests
        for f in self.request_dir.glob("*.json"):
            f.unlink()
        
        logging.info("Daemon cleanup complete")

def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    global daemon_service
    if daemon_service:
        daemon_service.cleanup()
    sys.exit(0)

def main():
    """Main daemon entry point."""
    global daemon_service
    
    # Set up signal handling
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start daemon
    logging.info("Starting Persistent Speech Daemon...")
    daemon_service = PersistentSpeechService()
    
    if daemon_service.is_ready:
        logging.info("Daemon ready - monitoring for requests...")
        daemon_service.monitor_requests()
    else:
        logging.error("Daemon failed to start")
        sys.exit(1)

if __name__ == "__main__":
    daemon_service = None
    main()