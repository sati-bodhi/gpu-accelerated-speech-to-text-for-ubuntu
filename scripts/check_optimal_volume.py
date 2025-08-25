#!/usr/bin/env python3
"""
Quick Microphone Volume Check
Provides recommendations for optimal volume based on current audio characteristics
"""
import subprocess
import numpy as np
import soundfile as sf

def get_current_mic_volume():
    """Get current microphone input volume percentage."""
    try:
        result = subprocess.run(['pactl', 'get-source-volume', '@DEFAULT_SOURCE@'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if 'Volume:' in line:
                    parts = line.split('/')
                    for part in parts:
                        if '%' in part:
                            return int(part.strip().replace('%', ''))
        return None
    except Exception:
        return None

def analyze_audio_quality(audio_file):
    """Analyze audio file and provide volume recommendations."""
    try:
        audio, sample_rate = sf.read(audio_file)
        if len(audio.shape) > 1:
            audio = np.mean(audio, axis=1)
        
        duration = len(audio) / sample_rate
        rms_level = np.sqrt(np.mean(audio**2))
        peak_level = np.max(np.abs(audio))
        
        # Quality assessment
        current_volume = get_current_mic_volume()
        
        print(f"=== Audio Quality Analysis ===")
        print(f"Current microphone volume: {current_volume}%")
        print(f"Audio duration: {duration:.2f}s")
        print(f"RMS level: {rms_level:.4f}")
        print(f"Peak level: {peak_level:.3f}")
        
        # Recommendations based on empirical testing
        if rms_level < 0.001:
            print("⚠️  VOLUME TOO LOW - Increase microphone volume to 60-80%")
            print("   First words likely to be cut off")
        elif rms_level > 0.05:
            print("⚠️  VOLUME TOO HIGH - Risk of clipping, reduce to 40-60%")
            print("   May cause transcription errors")
        elif peak_level > 0.95:
            print("⚠️  AUDIO CLIPPING DETECTED - Reduce microphone volume")
        else:
            print("✅ Audio levels look good for transcription")
            print("   This volume should preserve first words")
        
        # Specific recommendations
        if rms_level < 0.005:
            suggested_volume = min(80, (current_volume or 50) + 20)
            print(f"💡 Try increasing volume to: {suggested_volume}%")
        elif rms_level > 0.02:
            suggested_volume = max(40, (current_volume or 50) - 10)
            print(f"💡 Try reducing volume to: {suggested_volume}%")
        
    except Exception as e:
        print(f"Analysis failed: {e}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: check_optimal_volume.py <audio_file.wav>")
        sys.exit(1)
    
    analyze_audio_quality(sys.argv[1])