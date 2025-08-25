#!/usr/bin/env python3
"""
Session-Based Speech Daemon with Auto-Shutdown
Keeps model loaded during active sessions, releases VRAM when idle
"""

import os
import sys
import time
import json
import logging
import threading
from pathlib import Path
import signal
import queue

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
        logging.FileHandler('/tmp/session_daemon.log')
    ]
)

class SessionSpeechDaemon:
    """Session-aware speech daemon with smart VRAM management."""
    
    def __init__(self, session_timeout=600):  # 10 minutes default
        self.model = None
        self.device = None
        self.model_size = "large-v3"
        self.is_model_loaded = False
        self.last_activity = time.time()
        self.session_timeout = session_timeout
        self.processing = False
        self.shutdown_requested = False
        self.activity_lock = threading.Lock()
        
        # Audio calibration variables
        self.baseline_rms = None
        self.speech_contrast_data = []
        self.calibrated_threshold = 0.2  # Default fallback
        
        # IPC paths
        self.request_dir = Path("/tmp/speech_session_requests")
        self.response_dir = Path("/tmp/speech_session_responses")
        self.status_file = Path("/tmp/session_daemon_status.json")
        self.session_file = Path("/tmp/session_daemon_active")
        self.pid_file = Path("/tmp/session_daemon.pid")
        
        self.setup_directories()
        self.initialize_cuda_context()
        self.collect_baseline_rms()
        
        # Start session monitor thread
        self.monitor_thread = threading.Thread(target=self.monitor_session_timeout, daemon=True)
        self.monitor_thread.start()
        
        self.update_status()
    
    def setup_directories(self):
        """Create necessary directories for IPC."""
        self.request_dir.mkdir(exist_ok=True)
        self.response_dir.mkdir(exist_ok=True)
        
        # Create PID file for single-instance protection
        with open(self.pid_file, 'w') as f:
            f.write(str(os.getpid()))
        
        # Create session marker file
        with open(self.session_file, 'w') as f:
            json.dump({
                "started": time.time(),
                "pid": os.getpid()
            }, f)
        
        logging.info(f"Session daemon directories ready (PID: {os.getpid()})")
    
    def initialize_cuda_context(self):
        """Initialize device selection for model loading."""
        try:
            # Simple CUDA detection via nvidia-smi
            import subprocess
            result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
            if result.returncode == 0:
                self.device = "cuda"
                logging.info("CUDA device detected")
            else:
                self.device = "cpu" 
                logging.info("CUDA not available, using CPU")
        except Exception as e:
            logging.info(f"Device detection: using CPU (nvidia-smi failed: {e})")
            self.device = "cpu"
    
    def collect_baseline_rms(self):
        """Collect baseline ambient RMS level for calibration."""
        try:
            logging.info("Collecting baseline ambient RMS level...")
            
            # Record 3 seconds of ambient sound
            ambient_file = "/tmp/ambient_baseline.wav"
            import subprocess
            result = subprocess.run([
                "arecord", "-f", "S16_LE", "-r", "16000", "-c", "1", 
                "-d", "3", ambient_file
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                logging.warning(f"Ambient recording failed: {result.stderr}")
                self.baseline_rms = 0.01  # Conservative fallback
                return
            
            # Analyze the ambient audio
            audio, sample_rate = sf.read(ambient_file)
            if len(audio.shape) > 1:
                audio = np.mean(audio, axis=1)
            
            self.baseline_rms = np.sqrt(np.mean(audio**2))
            
            # Set initial calibrated threshold with reasonable buffer
            buffer_multiplier = 2.0  # Start conservative
            self.calibrated_threshold = max(0.1, self.baseline_rms * buffer_multiplier)
            
            logging.info(f"Baseline ambient RMS: {self.baseline_rms:.6f}")
            logging.info(f"Initial calibrated threshold: {self.calibrated_threshold:.3f}")
            
            # Clean up
            Path(ambient_file).unlink(missing_ok=True)
            
        except Exception as e:
            logging.error(f"Baseline RMS collection failed: {e}")
            self.baseline_rms = 0.01
            self.calibrated_threshold = 0.2
    
    def analyze_speech_contrast(self, audio):
        """Analyze speech levels vs baseline for dynamic calibration."""
        try:
            if self.baseline_rms is None:
                return
            
            # Calculate RMS of this audio segment
            speech_rms = np.sqrt(np.mean(audio**2))
            
            # Only analyze if speech is significantly above baseline
            if speech_rms > self.baseline_rms * 1.2:  # 20% above baseline
                contrast_ratio = speech_rms / self.baseline_rms
                self.speech_contrast_data.append({
                    'speech_rms': speech_rms,
                    'contrast_ratio': contrast_ratio,
                    'timestamp': time.time()
                })
                
                # Keep only recent data (last 10 measurements)
                self.speech_contrast_data = self.speech_contrast_data[-10:]
                
                # Recalibrate threshold based on collected data
                self.update_calibrated_threshold()
                
        except Exception as e:
            logging.warning(f"Speech contrast analysis failed: {e}")
    
    def update_calibrated_threshold(self):
        """Update VAD threshold based on speech contrast analysis."""
        if not self.speech_contrast_data or self.baseline_rms is None:
            return
        
        # Calculate average contrast ratio
        avg_contrast = np.mean([d['contrast_ratio'] for d in self.speech_contrast_data])
        
        # Set threshold to be halfway between baseline and typical speech level
        # This ensures we catch soft phonemes while avoiding ambient noise
        safety_buffer = 1.5  # 50% buffer above baseline
        new_threshold = self.baseline_rms * safety_buffer
        
        # Don't make threshold too sensitive or too aggressive
        new_threshold = max(0.05, min(0.4, new_threshold))
        
        if abs(new_threshold - self.calibrated_threshold) > 0.02:  # Significant change
            old_threshold = self.calibrated_threshold
            self.calibrated_threshold = new_threshold
            logging.info(f"Calibrated threshold updated: {old_threshold:.3f} → {new_threshold:.3f}")
            logging.info(f"Based on {len(self.speech_contrast_data)} samples, avg contrast: {avg_contrast:.1f}x")
    
    def load_model_on_demand(self):
        """Load model only when first needed."""
        if self.is_model_loaded:
            logging.info("Using cached model from session")
            return True
        
        try:
            logging.info(f"Loading {self.model_size} model for new session...")
            start_time = time.time()
            
            if self.device == "cuda":
                self.model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type="float16"
                )
            else:
                self.model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type="int8"
                )
            
            load_time = time.time() - start_time
            self.is_model_loaded = True
            
            logging.info(f"Model loaded in {load_time:.2f}s - SESSION ACTIVE")
            logging.info(f"Model will stay loaded for {self.session_timeout/60:.1f}min of activity")
            
            return True
            
        except Exception as e:
            logging.error(f"Model loading failed: {e}")
            return False
    
    def update_activity(self):
        """Update last activity timestamp and extend session."""
        with self.activity_lock:
            self.last_activity = time.time()
            
    def monitor_session_timeout(self):
        """Monitor for session inactivity and auto-shutdown."""
        logging.info(f"Session monitor started (timeout: {self.session_timeout}s)")
        
        while not self.shutdown_requested:
            try:
                with self.activity_lock:
                    inactive_time = time.time() - self.last_activity
                
                if inactive_time > self.session_timeout and self.is_model_loaded:
                    logging.info(f"Session inactive for {inactive_time:.1f}s, shutting down...")
                    self.shutdown_session()
                    break
                
                # Check every 30 seconds
                time.sleep(30)
                
            except Exception as e:
                logging.error(f"Session monitor error: {e}")
                time.sleep(60)
    
    def shutdown_session(self):
        """Gracefully shutdown and release VRAM."""
        logging.info("Shutting down session daemon...")
        
        if self.is_model_loaded and self.model:
            del self.model
            self.model = None
            self.is_model_loaded = False
            logging.info("Model unloaded, VRAM released back to system")
        
        # Clean up session files
        try:
            if self.pid_file.exists():
                self.pid_file.unlink()
            if self.session_file.exists():
                self.session_file.unlink()
            if self.status_file.exists():
                self.status_file.unlink()
        except Exception:
            pass
        
        self.shutdown_requested = True
        logging.info("Session daemon shutdown complete")
    
    def update_status(self):
        """Update daemon status file."""
        status = {
            "active": not self.shutdown_requested,
            "model_loaded": self.is_model_loaded,
            "device": self.device,
            "model_size": self.model_size,
            "processing": self.processing,
            "last_activity": self.last_activity,
            "session_timeout": self.session_timeout,
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
            if duration < 0.15:
                return False
                
            rms_level = np.sqrt(np.mean(audio**2))
            if rms_level < 0.0005:
                return False
                
            return True
            
        except Exception:
            return True
    
    def transcribe_audio(self, audio_file):
        """Transcribe audio using session model."""
        # Update activity - extends session
        self.update_activity()
        
        self.processing = True
        self.update_status()
        
        try:
            # Load audio
            audio, sample_rate = sf.read(audio_file)
            audio = audio.astype('float32')
            
            if len(audio.shape) > 1:
                audio = np.mean(audio, axis=1)
            
            # Analyze speech-to-ambient contrast for calibration
            self.analyze_speech_contrast(audio)
            
            # Pre-filter empty audio
            if not self.check_audio_content(audio, sample_rate):
                logging.info("Skipping empty audio - session extended")
                return []
            
            # Load model on-demand for session
            if not self.load_model_on_demand():
                return []
            
            # Transcribe with session model
            start_time = time.time()
            segments, info = self.model.transcribe(
                audio,
                language="en",
                beam_size=5,
                best_of=5,
                temperature=0,
                vad_filter=True,
                vad_parameters=dict(
                    threshold=self.calibrated_threshold,  # Dynamic threshold based on ambient calibration
                    min_silence_duration_ms=500,
                    min_speech_duration_ms=100
                )
            )
            
            # Extract results
            results = []
            for seg in segments:
                text = seg.text.strip()
                if text:
                    results.append(text)
            
            transcribe_time = time.time() - start_time
            
            if self.is_model_loaded:
                logging.info(f"SESSION transcription: {transcribe_time:.3f}s (model cached)")
            else:
                logging.info(f"Transcription: {transcribe_time:.3f}s")
            
            logging.info(f"Session will stay active until {time.strftime('%H:%M:%S', time.localtime(time.time() + self.session_timeout))}")
            
            return results
            
        except Exception as e:
            logging.error(f"Transcription failed: {e}")
            return []
        finally:
            self.processing = False
            self.update_status()
    
    def process_request(self, request_file):
        """Process a single transcription request."""
        try:
            with open(request_file, 'r') as f:
                request = json.load(f)
            
            request_id = request.get('id')
            request_type = request.get('type', 'transcribe')
            
            logging.info(f"Processing session request {request_id} (type: {request_type})")
            
            # Handle ping requests for responsiveness testing
            if request_type == 'ping':
                logging.info(f"Ping request received: {request_id}")
                response = {
                    'id': request_id,
                    'type': 'pong',
                    'timestamp': time.time(),
                    'device': self.device,
                    'session_active': self.is_model_loaded
                }
            else:
                # Handle normal transcription requests
                audio_file = request.get('audio_file')
                results = self.transcribe_audio(audio_file)
                
                response = {
                    'id': request_id,
                    'results': results,
                    'timestamp': time.time(),
                    'device': self.device,
                    'session_active': self.is_model_loaded
                }
            
            response_file = self.response_dir / f"{request_id}.json"
            with open(response_file, 'w') as f:
                json.dump(response, f)
            
            # Auto-type results (skip for ping requests)
            if request_type != 'ping' and 'results' in response:
                for text in response['results']:
                    try:
                        pyautogui.typewrite(text + ' ')
                        logging.info(f"Typed: {text}")
                    except Exception as e:
                        logging.warning(f"Typing failed: {e}")
            
            # Clean up request
            request_file.unlink()
            
        except Exception as e:
            logging.error(f"Request processing failed: {e}")
    
    def run(self):
        """Main daemon loop."""
        logging.info("Session daemon started - waiting for requests...")
        
        while not self.shutdown_requested:
            try:
                # Check for new requests
                request_files = list(self.request_dir.glob("*.json"))
                
                for request_file in request_files:
                    if self.shutdown_requested:
                        break
                    self.process_request(request_file)
                
                # Brief pause
                time.sleep(0.1)
                
            except KeyboardInterrupt:
                logging.info("Received shutdown signal")
                break
            except Exception as e:
                logging.error(f"Daemon error: {e}")
                time.sleep(1)
        
        self.shutdown_session()

def check_existing_daemon():
    """Check if daemon is already running and responsive."""
    pid_file = Path("/tmp/session_daemon.pid")
    
    # Check if PID file exists
    if not pid_file.exists():
        return False
    
    try:
        with open(pid_file, 'r') as f:
            pid = int(f.read().strip())
        
        # Check if process is actually running
        os.kill(pid, 0)  # Send signal 0 to check if process exists
        
        # Check if daemon is responsive (status file updated recently)
        status_file = Path("/tmp/session_daemon_status.json")
        if status_file.exists():
            with open(status_file, 'r') as f:
                status = json.load(f)
            
            # Consider daemon responsive if status updated within last 60 seconds
            if time.time() - status.get('timestamp', 0) < 60:
                logging.info(f"Found responsive daemon with PID {pid}")
                return True
        
        # Process exists but daemon not responsive - clean up stale PID file
        logging.warning(f"Found unresponsive daemon with PID {pid}, cleaning up...")
        pid_file.unlink()
        return False
        
    except (ValueError, ProcessLookupError, FileNotFoundError):
        # PID file invalid or process not found - clean up
        try:
            pid_file.unlink()
        except FileNotFoundError:
            pass
        return False

def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    global daemon
    if daemon:
        daemon.shutdown_session()
    sys.exit(0)

def main():
    """Main daemon entry point."""
    global daemon
    
    # Check if daemon is already running
    if check_existing_daemon():
        logging.info("Session daemon already running - exiting")
        sys.exit(0)
    
    # Set up signal handling
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Parse arguments for session timeout
    session_timeout = 600  # 10 minutes default
    if len(sys.argv) > 1:
        try:
            session_timeout = int(sys.argv[1])
        except ValueError:
            logging.warning("Invalid timeout, using default 10 minutes")
    
    # Create and start session daemon
    logging.info(f"Starting Session Speech Daemon (timeout: {session_timeout/60:.1f}min)...")
    daemon = SessionSpeechDaemon(session_timeout=session_timeout)
    daemon.run()

if __name__ == "__main__":
    daemon = None
    main()