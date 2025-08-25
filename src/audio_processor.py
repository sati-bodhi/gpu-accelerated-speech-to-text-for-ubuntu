#!/usr/bin/env python3
"""
Audio Preprocessing Service

Handles noise cancelling, audio quality analysis, and content validation
for speech-to-text processing. Separated from main daemon for modularity.
"""

import logging
import numpy as np
import soundfile as sf
from scipy import signal as scipy_signal
from scipy.fft import fft, ifft
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class AudioAnalysis:
    """Results from audio content analysis."""
    duration: float
    rms_level: float
    peak_level: float
    has_content: bool
    sample_rate: int


@dataclass
class ProcessedAudio:
    """Results from audio preprocessing."""
    audio: np.ndarray
    sample_rate: int
    analysis: AudioAnalysis
    preprocessing_applied: bool
    debug_file: Optional[str] = None


class AudioPreprocessor:
    """
    Service for audio preprocessing and quality analysis.
    
    Responsibilities:
    - Noise cancelling (high-pass filtering + spectral subtraction)
    - Audio content validation (silence detection)
    - Quality analysis and metrics
    - Debug output generation
    """
    
    def __init__(self, enable_debug=True):
        self.enable_debug = enable_debug
        self.logger = logging.getLogger(__name__)
        
        # Noise cancelling parameters
        self.high_pass_cutoff_hz = 80  # Remove AC hum and rumble
        self.spectral_reduction_factor = 1.5
        self.noise_floor_ratio = 0.1  # Minimum signal retention
        self.normalization_headroom = 0.95
        
        # Content validation thresholds
        self.min_duration_seconds = 0.15
        self.min_rms_threshold = 0.0005
    
    def load_and_normalize_audio(self, audio_file: str) -> Tuple[np.ndarray, int]:
        """Load audio file and convert to mono float32."""
        try:
            audio, sample_rate = sf.read(audio_file)
            audio = audio.astype('float32')
            
            # Convert stereo to mono if needed
            if len(audio.shape) > 1:
                audio = np.mean(audio, axis=1)
            
            return audio, sample_rate
            
        except Exception as e:
            self.logger.error(f"Audio loading failed: {e}")
            raise
    
    def analyze_audio_content(self, audio: np.ndarray, sample_rate: int) -> AudioAnalysis:
        """Analyze audio for content validation and quality metrics."""
        try:
            duration = len(audio) / sample_rate
            rms_level = np.sqrt(np.mean(audio**2))
            peak_level = np.max(np.abs(audio))
            
            # Content validation
            has_content = (
                duration >= self.min_duration_seconds and 
                rms_level >= self.min_rms_threshold
            )
            
            return AudioAnalysis(
                duration=float(duration),
                rms_level=float(rms_level),
                peak_level=float(peak_level),
                has_content=bool(has_content),
                sample_rate=int(sample_rate)
            )
            
        except Exception as e:
            self.logger.warning(f"Audio analysis failed: {e}")
            # Return conservative defaults
            return AudioAnalysis(
                duration=float(0.0),
                rms_level=float(0.0),
                peak_level=float(0.0),
                has_content=bool(False),
                sample_rate=int(sample_rate)
            )
    
    def apply_noise_cancelling(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """
        Apply noise cancelling preprocessing.
        
        Steps:
        1. High-pass filter to remove low-frequency noise (AC hum, rumble)
        2. Spectral subtraction for background noise reduction  
        3. Normalization to prevent clipping while preserving dynamics
        """
        try:
            original_audio = audio.copy()
            
            # 1. High-pass filter to remove low-frequency noise
            nyquist = sample_rate / 2
            high_cutoff = self.high_pass_cutoff_hz / nyquist
            b, a = scipy_signal.butter(4, high_cutoff, btype='high')
            audio = scipy_signal.filtfilt(b, a, audio)
            
            # 2. Simple spectral subtraction for background noise reduction
            # Estimate noise from first 0.2 seconds (assumed to be relatively quiet)
            noise_samples = min(int(0.2 * sample_rate), len(audio) // 4)
            if noise_samples > 100:  # Only if we have enough samples
                noise_spectrum = np.abs(fft(audio[:noise_samples]))
                noise_power = np.mean(noise_spectrum)
                
                # Apply spectral subtraction with conservative parameters
                audio_fft = fft(audio)
                audio_magnitude = np.abs(audio_fft)
                audio_phase = np.angle(audio_fft)
                
                # Subtract estimated noise (conservative factor to avoid artifacts)
                cleaned_magnitude = audio_magnitude - self.spectral_reduction_factor * noise_power
                cleaned_magnitude = np.maximum(cleaned_magnitude, self.noise_floor_ratio * audio_magnitude)
                
                # Reconstruct audio
                cleaned_fft = cleaned_magnitude * np.exp(1j * audio_phase)
                audio = np.real(ifft(cleaned_fft))
            
            # 3. Normalize to prevent clipping but preserve dynamics
            max_val = np.max(np.abs(audio))
            if max_val > 0:
                audio = audio * (self.normalization_headroom / max_val)
            
            self.logger.info("Applied noise cancelling: high-pass filter + spectral subtraction")
            return audio.astype(np.float32)
            
        except Exception as e:
            self.logger.warning(f"Noise cancelling failed, using original audio: {e}")
            return original_audio
    
    def save_debug_audio(self, audio: np.ndarray, sample_rate: int) -> Optional[str]:
        """Save processed audio for debugging and playback testing."""
        if not self.enable_debug:
            return None
            
        try:
            debug_file = "/tmp/processed_audio_debug.wav"
            sf.write(debug_file, audio, sample_rate)
            self.logger.info(f"Saved processed audio to {debug_file} for playback testing")
            return debug_file
            
        except Exception as e:
            self.logger.warning(f"Could not save debug audio: {e}")
            return None
    
    def process_audio_file(self, audio_file: str) -> ProcessedAudio:
        """
        Complete audio preprocessing pipeline.
        
        Returns ProcessedAudio with analysis, processed audio, and debug info.
        """
        try:
            # Load and normalize audio
            audio, sample_rate = self.load_and_normalize_audio(audio_file)
            
            # Analyze content before processing
            analysis = self.analyze_audio_content(audio, sample_rate)
            
            # Skip processing if no content detected
            if not analysis.has_content:
                self.logger.info(f"Skipping empty audio - duration: {analysis.duration:.3f}s, RMS: {analysis.rms_level:.6f}")
                return ProcessedAudio(
                    audio=audio,
                    sample_rate=sample_rate,
                    analysis=analysis,
                    preprocessing_applied=False
                )
            
            # Apply noise cancelling preprocessing
            processed_audio = self.apply_noise_cancelling(audio, sample_rate)
            
            # Save debug output
            debug_file = self.save_debug_audio(processed_audio, sample_rate)
            
            return ProcessedAudio(
                audio=processed_audio,
                sample_rate=sample_rate,
                analysis=analysis,
                preprocessing_applied=True,
                debug_file=debug_file
            )
            
        except Exception as e:
            self.logger.error(f"Audio preprocessing failed: {e}")
            raise
    
    def analyze_ambient_levels(self, audio_file: str) -> AudioAnalysis:
        """Analyze ambient audio levels for VAD threshold calibration."""
        try:
            audio, sample_rate = self.load_and_normalize_audio(audio_file)
            return self.analyze_audio_content(audio, sample_rate)
            
        except Exception as e:
            self.logger.error(f"Ambient analysis failed: {e}")
            raise


# Convenience function for backward compatibility
def preprocess_audio_file(audio_file: str, enable_debug: bool = True) -> ProcessedAudio:
    """Standalone function for audio preprocessing."""
    processor = AudioPreprocessor(enable_debug=enable_debug)
    return processor.process_audio_file(audio_file)


if __name__ == "__main__":
    # Test the audio processor
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 audio_processor.py <audio_file>")
        sys.exit(1)
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Process test file
    processor = AudioPreprocessor()
    result = processor.process_audio_file(sys.argv[1])
    
    print(f"\n=== Audio Processing Results ===")
    print(f"Duration: {result.analysis.duration:.3f}s")
    print(f"RMS Level: {result.analysis.rms_level:.6f}")
    print(f"Peak Level: {result.analysis.peak_level:.6f}")
    print(f"Has Content: {result.analysis.has_content}")
    print(f"Preprocessing Applied: {result.preprocessing_applied}")
    if result.debug_file:
        print(f"Debug File: {result.debug_file}")