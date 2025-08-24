#!/usr/bin/env python3
"""
Optimized GPU-accelerated speech-to-text processor with persistent model loading.
"""

import os
import sys
import time
import logging

# Set up CUDNN library path before importing anything else
def setup_cuda_env():
    """Set up CUDA environment variables for proper library loading."""
    try:
        # Get the virtual environment path
        venv_path = os.path.dirname(os.path.dirname(sys.executable))
        
        # CUDNN and CUBLAS library paths
        cudnn_lib_path = os.path.join(venv_path, 'lib/python3.10/site-packages/nvidia/cudnn/lib')
        cublas_lib_path = os.path.join(venv_path, 'lib/python3.10/site-packages/nvidia/cublas/lib')
        
        # Set LD_LIBRARY_PATH
        current_path = os.environ.get('LD_LIBRARY_PATH', '')
        new_paths = [cudnn_lib_path, cublas_lib_path]
        
        if current_path:
            new_paths.append(current_path)
            
        os.environ['LD_LIBRARY_PATH'] = ':'.join(new_paths)
        
        print(f"CUDA environment setup:")
        print(f"  CUDNN path: {cudnn_lib_path}")
        print(f"  CUBLAS path: {cublas_lib_path}")
        print(f"  LD_LIBRARY_PATH: {os.environ['LD_LIBRARY_PATH']}")
        
        return True
        
    except Exception as e:
        print(f"Warning: Could not set up CUDA environment: {e}")
        return False

# Set up CUDA environment first
setup_cuda_env()

try:
    import numpy as np
    import pyautogui
    import soundfile as sf
    from faster_whisper import WhisperModel
except ImportError as e:
    print(f"Error: Required library not found: {e}")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/speech_to_text.log')
    ]
)

class OptimizedWhisperService:
    """Persistent Whisper model service for optimized performance."""
    
    def __init__(self):
        self.model = None
        self.device = None
        self.model_size = None
        self.compute_type = None
        self.load_model()
    
    def load_model(self):
        """Load and cache Whisper model in memory."""
        try:
            # Try GPU first, fall back to CPU if needed
            self.device = "cuda"
            self.compute_type = "float16"
            self.model_size = "large-v3"
            
            try:
                logging.info(f"Loading Whisper {self.model_size} model on GPU (persistent)...")
                start_time = time.time()
                self.model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
                load_time = time.time() - start_time
                logging.info(f"Model loaded and cached in {load_time:.2f}s")
                logging.info(f"Model ready for persistent inference on {self.device.upper()}")
            except Exception as gpu_error:
                logging.warning(f"GPU initialization failed: {gpu_error}")
                logging.info("Falling back to CPU with persistent model...")
                self.device = "cpu"
                self.compute_type = "int8"
                self.model_size = "large-v3"
                self.model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
                logging.info(f"Model cached on {self.device.upper()}")
                
        except Exception as e:
            logging.error(f"Model loading failed: {e}")
            sys.exit(1)
    
    def check_audio_content(self, audio, sample_rate):
        """Pre-filter empty or silent audio before GPU processing."""
        try:
            # Calculate basic audio metrics
            duration = len(audio) / sample_rate
            rms_level = np.sqrt(np.mean(audio**2)) if len(audio) > 0 else 0
            max_amplitude = np.max(np.abs(audio)) if len(audio) > 0 else 0
            
            # Thresholds for content detection
            min_duration = 0.25  # 250ms minimum
            min_rms = 0.001      # Minimum RMS level
            min_amplitude = 0.01  # Minimum peak amplitude
            
            logging.info(f"Audio check: duration={duration:.3f}s, rms={rms_level:.4f}, peak={max_amplitude:.4f}")
            
            # Check if audio likely contains speech
            has_content = (
                duration >= min_duration and 
                rms_level >= min_rms and 
                max_amplitude >= min_amplitude
            )
            
            if not has_content:
                logging.info(f"Audio pre-filter: Skipping processing (silent/empty audio)")
                return False
                
            logging.info(f"Audio pre-filter: Content detected, proceeding with transcription")
            return True
            
        except Exception as e:
            logging.warning(f"Audio content check failed: {e}, proceeding anyway")
            return True
    
    def transcribe_audio(self, audio):
        """Transcribe audio using persistent cached model."""
        try:
            # Pre-filter empty audio before expensive GPU processing
            if not self.check_audio_content(audio, 16000):
                logging.info("Skipping transcription for empty/silent audio")
                return []
            
            logging.info("Starting transcription with persistent model...")
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
            
            # Process segments
            results = []
            for seg in segments:
                text = seg.text.strip()
                if text:
                    results.append(text)
                    logging.info(f"Recognized: {text}")
            
            transcribe_time = time.time() - start_time
            logging.info(f"Transcription completed in {transcribe_time:.2f}s: {len(results)} segments")
            logging.info(f"Using cached {self.device.upper()} model (no loading overhead)")
            return results
            
        except Exception as e:
            logging.error(f"Transcription failed: {e}")
            return []

# Global persistent service instance
whisper_service = None

def log_user_info():
    """Log current user information."""
    try:
        uid = os.geteuid()
        import pwd
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

def type_text(text):
    """Type text using pyautogui."""
    try:
        logging.info(f"Typing: {text}")
        pyautogui.typewrite(text + ' ')
    except Exception as e:
        logging.error(f"Failed to type text: {e}")

def main():
    """Main function."""
    global whisper_service
    
    # Check arguments
    if len(sys.argv) < 2:
        print("Usage: python gpu_service_optimized.py <audio_file>")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    
    # Log user info
    log_user_info()
    
    # Initialize persistent service (one-time model loading)
    if whisper_service is None:
        logging.info("Initializing persistent Whisper service...")
        whisper_service = OptimizedWhisperService()
        logging.info("Persistent service ready for high-speed inference")
    else:
        logging.info("Using existing persistent service (zero loading time)")
    
    # Process audio
    logging.info(f"Processing audio file: {audio_file}")
    
    # Load audio
    audio = load_audio(audio_file)
    
    # Transcribe with persistent model
    segments = whisper_service.transcribe_audio(audio)
    
    # Type results
    for segment in segments:
        type_text(segment)
    
    logging.info("Processing completed")

if __name__ == "__main__":
    main()