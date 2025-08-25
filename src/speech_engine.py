#!/usr/bin/env python3
"""
Speech Recognition Engine

Handles Whisper speech-to-text engine lifecycle, CUDA setup, and transcription processing.
Separated from main daemon for focused speech recognition responsibility and testability.
"""

import os
import sys
import time
import logging
import subprocess
import numpy as np
from typing import List, Optional, Tuple
from dataclasses import dataclass

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None


@dataclass
class TranscriptionResult:
    """Results from model transcription."""
    segments: List[str]
    processing_time: float
    device_used: str
    model_size: str
    success: bool
    error_message: Optional[str] = None


@dataclass
class VADParameters:
    """Voice Activity Detection configuration."""
    threshold: float
    min_silence_duration_ms: int
    min_speech_duration_ms: int


class SpeechEngine:
    """
    Service for Whisper speech recognition engine and transcription.
    
    Responsibilities:
    - CUDA environment setup and device detection
    - Whisper engine loading and caching with VRAM management
    - Speech transcription processing with VAD optimization
    - Performance monitoring and error handling
    """
    
    def __init__(self, model_size: str = "large-v3", vad_threshold: float = 0.16):
        self.model = None
        self.model_size = model_size
        self.device = None
        self.is_model_loaded = False
        self.logger = logging.getLogger(__name__)
        
        # VAD parameters optimized for phoneme preservation
        self.vad_params = VADParameters(
            threshold=vad_threshold,  # Calibrated just above ambient RMS
            min_silence_duration_ms=500,
            min_speech_duration_ms=100
        )
        
        self._initialize_device()
    
    def _initialize_device(self):
        """Initialize CUDA device detection."""
        try:
            # Simple CUDA detection via nvidia-smi
            result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
            if result.returncode == 0:
                self.device = "cuda"
                self.logger.info("CUDA device detected for model processing")
            else:
                self.device = "cpu"
                self.logger.info("CUDA not available, using CPU for model processing")
        except Exception as e:
            self.logger.info(f"Device detection: using CPU (nvidia-smi failed: {e})")
            self.device = "cpu"
    
    def setup_cuda_environment(self) -> bool:
        """Set up CUDA environment variables for model loading."""
        try:
            venv_path = os.path.dirname(os.path.dirname(sys.executable))
            cudnn_lib_path = os.path.join(venv_path, 'lib/python3.10/site-packages/nvidia/cudnn/lib')
            cublas_lib_path = os.path.join(venv_path, 'lib/python3.10/site-packages/nvidia/cublas/lib')
            
            current_path = os.environ.get('LD_LIBRARY_PATH', '')
            new_paths = [cudnn_lib_path, cublas_lib_path]
            if current_path:
                new_paths.append(current_path)
            os.environ['LD_LIBRARY_PATH'] = ':'.join(new_paths)
            
            self.logger.info("CUDA environment configured for model loading")
            return True
            
        except Exception as e:
            self.logger.warning(f"CUDA environment setup failed: {e}")
            return False
    
    def load_model(self) -> bool:
        """Load Whisper model with optimal configuration."""
        if self.is_model_loaded:
            self.logger.info("Model already loaded - using cached instance")
            return True
        
        if WhisperModel is None:
            self.logger.error("faster-whisper not available")
            return False
        
        try:
            self.logger.info(f"Loading {self.model_size} model...")
            start_time = time.time()
            
            # Setup CUDA environment
            if self.device == "cuda":
                self.setup_cuda_environment()
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
            
            self.logger.info(f"Model loaded in {load_time:.2f}s using {self.device}")
            return True
            
        except Exception as e:
            self.logger.error(f"Model loading failed: {e}")
            return False
    
    def transcribe_audio(self, audio: np.ndarray, sample_rate: int = 16000) -> TranscriptionResult:
        """
        Transcribe audio using loaded model with VAD optimization.
        
        Args:
            audio: Preprocessed audio data
            sample_rate: Audio sample rate (default 16000)
            
        Returns:
            TranscriptionResult with segments and performance metrics
        """
        if not self.is_model_loaded:
            if not self.load_model():
                return TranscriptionResult(
                    segments=[],
                    processing_time=0.0,
                    device_used=self.device,
                    model_size=self.model_size,
                    success=False,
                    error_message="Model loading failed"
                )
        
        try:
            start_time = time.time()
            
            # Transcribe with optimized VAD parameters
            segments, info = self.model.transcribe(
                audio,
                language="en",
                beam_size=5,
                best_of=5,
                temperature=0,
                vad_filter=True,
                vad_parameters=dict(
                    threshold=self.vad_params.threshold,
                    min_silence_duration_ms=self.vad_params.min_silence_duration_ms,
                    min_speech_duration_ms=self.vad_params.min_speech_duration_ms
                )
            )
            
            # Extract text segments
            results = []
            for seg in segments:
                text = seg.text.strip()
                if text:
                    results.append(text)
            
            processing_time = time.time() - start_time
            
            self.logger.info(f"Transcription completed in {processing_time:.3f}s")
            self.logger.info(f"VAD threshold: {self.vad_params.threshold} (optimized for phoneme preservation)")
            
            return TranscriptionResult(
                segments=results,
                processing_time=processing_time,
                device_used=self.device,
                model_size=self.model_size,
                success=True
            )
            
        except Exception as e:
            self.logger.error(f"Transcription failed: {e}")
            return TranscriptionResult(
                segments=[],
                processing_time=0.0,
                device_used=self.device,
                model_size=self.model_size,
                success=False,
                error_message=str(e)
            )
    
    def update_vad_threshold(self, new_threshold: float):
        """Update VAD threshold for phoneme preservation tuning."""
        old_threshold = self.vad_params.threshold
        self.vad_params.threshold = new_threshold
        self.logger.info(f"VAD threshold updated: {old_threshold} → {new_threshold}")
    
    def get_vad_parameters(self) -> VADParameters:
        """Get current VAD configuration."""
        return self.vad_params
    
    def release_model(self):
        """Release model and free VRAM."""
        if self.is_model_loaded and self.model:
            del self.model
            self.model = None
            self.is_model_loaded = False
            self.logger.info("Model released, VRAM freed")
    
    def get_model_status(self) -> dict:
        """Get current model status for monitoring."""
        return {
            "loaded": self.is_model_loaded,
            "device": self.device,
            "model_size": self.model_size,
            "vad_threshold": self.vad_params.threshold
        }


# Convenience function for standalone transcription
def transcribe_audio_file(audio_file: str, model_size: str = "large-v3", vad_threshold: float = 0.16) -> TranscriptionResult:
    """Standalone function for audio transcription."""
    import soundfile as sf
    
    # Load audio
    audio, sample_rate = sf.read(audio_file)
    if len(audio.shape) > 1:
        audio = np.mean(audio, axis=1)
    
    # Transcribe
    engine = SpeechEngine(model_size=model_size, vad_threshold=vad_threshold)
    return engine.transcribe_audio(audio.astype(np.float32), sample_rate)


if __name__ == "__main__":
    # Test the speech engine
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 speech_engine.py <audio_file>")
        sys.exit(1)
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Test transcription
    result = transcribe_audio_file(sys.argv[1])
    
    print(f"\n=== Speech Engine Transcription Results ===")
    print(f"Success: {result.success}")
    print(f"Device: {result.device_used}")
    print(f"Model: {result.model_size}")
    print(f"Processing Time: {result.processing_time:.3f}s")
    
    if result.success:
        print(f"Segments ({len(result.segments)}):")
        for i, text in enumerate(result.segments, 1):
            print(f"  {i}. {text}")
    else:
        print(f"Error: {result.error_message}")