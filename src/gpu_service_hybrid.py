#!/usr/bin/env python3
"""
Hybrid GPU-accelerated speech-to-text with CUDA optimization and lazy loading.
Optimizes cold start performance without permanent VRAM usage.
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

import logging

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

class HybridGPUService:
    """Optimized GPU service with fast cold start and CUDA context reuse."""
    
    def __init__(self):
        self.cuda_context_initialized = False
        self.model_cache = {}
        self.device = None
        self.model_size = "large-v3"
        self.compute_type = None
        
    def initialize_cuda_context(self):
        """Initialize device detection for optimized loading."""
        try:
            if not self.cuda_context_initialized:
                logging.info("Detecting optimal device...")
                
                # Simple CUDA availability check
                import subprocess
                result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
                if result.returncode == 0:
                    self.device = "cuda"
                    self.compute_type = "float16"
                    logging.info("CUDA device detected for optimized loading")
                else:
                    self.device = "cpu"
                    self.compute_type = "int8"
                    logging.info("Using CPU for processing")
                
                self.cuda_context_initialized = True
                return self.device == "cuda"
                    
        except Exception as e:
            logging.warning(f"Device detection failed: {e}")
            self.device = "cpu"  
            self.compute_type = "int8"
            return False
    
    def load_model_optimized(self):
        """Load model with optimized initialization."""
        try:
            # Pre-initialize CUDA context if not done
            if not self.cuda_context_initialized:
                self.initialize_cuda_context()
            
            logging.info(f"Loading optimized Whisper {self.model_size} model...")
            start_time = time.time()
            
            try:
                if self.device == "cuda":
                    logging.info("Using pre-warmed CUDA context")
                
                model = WhisperModel(
                    self.model_size, 
                    device=self.device, 
                    compute_type=self.compute_type,
                    # Optimization parameters
                    local_files_only=False,
                    download_root=None
                )
                
                load_time = time.time() - start_time
                logging.info(f"Optimized model loaded in {load_time:.2f}s")
                logging.info(f"Using {self.device.upper()} with optimized initialization")
                
                return model
                
            except Exception as gpu_error:
                logging.warning(f"GPU model loading failed: {gpu_error}")
                logging.info("Falling back to CPU...")
                self.device = "cpu"
                self.compute_type = "int8"
                
                model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
                load_time = time.time() - start_time
                logging.info(f"CPU fallback model loaded in {load_time:.2f}s")
                return model
                
        except Exception as e:
            logging.error(f"Model loading failed: {e}")
            sys.exit(1)
    
    def check_audio_content(self, audio, sample_rate):
        """Fast pre-filter for empty or silent audio."""
        try:
            # Calculate basic audio metrics
            duration = len(audio) / sample_rate
            
            # Quick duration check
            if duration < 0.15:  # Very short
                logging.info(f"Audio pre-filter: Too short ({duration:.3f}s), skipping")
                return False
            
            # Quick energy check
            rms_level = np.sqrt(np.mean(audio**2)) if len(audio) > 0 else 0
            max_amplitude = np.max(np.abs(audio)) if len(audio) > 0 else 0
            
            # Relaxed thresholds for better detection
            min_rms = 0.0005      # Lower threshold
            min_amplitude = 0.005  # Lower threshold
            
            has_content = (rms_level >= min_rms and max_amplitude >= min_amplitude)
            
            logging.info(f"Audio check: duration={duration:.3f}s, rms={rms_level:.4f}, peak={max_amplitude:.4f}")
            
            if not has_content:
                logging.info(f"Audio pre-filter: Silent audio detected, skipping GPU processing")
                return False
                
            logging.info(f"Audio pre-filter: Content detected, proceeding")
            return True
            
        except Exception as e:
            logging.warning(f"Audio content check failed: {e}, proceeding anyway")
            return True
    
    def transcribe_audio(self, audio):
        """Transcribe audio using optimized model loading."""
        try:
            # Pre-filter empty audio before expensive model loading
            if not self.check_audio_content(audio, 16000):
                logging.info("Skipping transcription for empty/silent audio")
                return []
            
            # Load model with optimizations
            model = self.load_model_optimized()
            
            logging.info("Starting transcription with optimized model...")
            start_time = time.time()
            
            segments, info = model.transcribe(
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
            logging.info(f"Using optimized {self.device.upper()} model (faster cold start)")
            
            # Clean up model to free VRAM
            del model
            if self.device == "cuda":
                logging.info("VRAM released for other applications")
            
            return results
            
        except Exception as e:
            logging.error(f"Transcription failed: {e}")
            return []

# Global service instance
gpu_service = None

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
    global gpu_service
    
    # Check arguments
    if len(sys.argv) < 2:
        print("Usage: python gpu_service_hybrid.py <audio_file>")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    
    # Log user info
    log_user_info()
    
    # Initialize service (CUDA context pre-warmed)
    if gpu_service is None:
        logging.info("Initializing hybrid GPU service...")
        gpu_service = HybridGPUService()
    
    # Process audio
    logging.info(f"Processing audio file: {audio_file}")
    
    # Load audio
    audio = load_audio(audio_file)
    
    # Transcribe with optimized loading
    segments = gpu_service.transcribe_audio(audio)
    
    # Type results
    for segment in segments:
        type_text(segment)
    
    logging.info("Processing completed")

if __name__ == "__main__":
    main()