#!/usr/bin/env python3
"""
Audio Level Testing Script
Tests different microphone levels to find optimal range for speech recognition
"""
import os
import sys
import time
import json
import subprocess
import numpy as np
import soundfile as sf
from pathlib import Path

def get_current_mic_volume():
    """Get current microphone input volume."""
    try:
        result = subprocess.run(['pactl', 'get-source-volume', '@DEFAULT_SOURCE@'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            # Parse volume from output like "Volume: front-left: 65536 / 100% ..."
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if 'Volume:' in line:
                    # Extract percentage
                    parts = line.split('/')
                    for part in parts:
                        if '%' in part:
                            return int(part.strip().replace('%', ''))
        return None
    except Exception as e:
        print(f"Failed to get microphone volume: {e}")
        return None

def set_mic_volume(percentage):
    """Set microphone input volume to specified percentage."""
    try:
        subprocess.run(['pactl', 'set-source-volume', '@DEFAULT_SOURCE@', f'{percentage}%'], 
                      check=True)
        return True
    except Exception as e:
        print(f"Failed to set microphone volume: {e}")
        return False

def analyze_audio_levels(audio_file):
    """Analyze audio file for level metrics."""
    try:
        audio, sample_rate = sf.read(audio_file)
        if len(audio.shape) > 1:
            audio = np.mean(audio, axis=1)
        
        # Calculate audio metrics
        duration = len(audio) / sample_rate
        rms_level = np.sqrt(np.mean(audio**2))
        peak_level = np.max(np.abs(audio))
        
        # Check for clipping (values near ±1.0)
        clipping = np.sum(np.abs(audio) > 0.99) / len(audio)
        
        # Signal-to-noise estimate (energy in first vs last 10%)
        first_10 = audio[:len(audio)//10]
        last_10 = audio[-len(audio)//10:]
        snr_estimate = np.mean(first_10**2) / (np.mean(last_10**2) + 1e-10)
        
        return {
            'duration': duration,
            'rms_level': float(rms_level),
            'peak_level': float(peak_level),
            'clipping_ratio': float(clipping),
            'snr_estimate': float(snr_estimate)
        }
    except Exception as e:
        print(f"Audio analysis failed: {e}")
        return None

def test_transcription_at_volume(volume_pct, test_audio_file):
    """Test transcription quality at specific volume level."""
    print(f"Testing volume {volume_pct}% ...")
    
    # Set volume
    if not set_mic_volume(volume_pct):
        return None
    
    # Wait for volume change to take effect
    time.sleep(0.5)
    
    # Analyze audio characteristics
    audio_metrics = analyze_audio_levels(test_audio_file)
    if not audio_metrics:
        return None
    
    # Test with session daemon
    try:
        result = subprocess.run([
            '/home/sati/speech-to-text-for-ubuntu/scripts/run_gpu_speech_session.sh',
            test_audio_file
        ], capture_output=True, text=True, timeout=30)
        
        # Check for recent response file
        response_dir = Path('/tmp/speech_session_responses')
        response_files = sorted(response_dir.glob('*.json'), key=lambda p: p.stat().st_mtime)
        
        if response_files:
            latest_response = response_files[-1]
            with open(latest_response, 'r') as f:
                response = json.load(f)
            
            results = response.get('results', [])
            transcription_success = len(results) > 0
            
            return {
                'volume_pct': volume_pct,
                'transcription_success': transcription_success,
                'results_count': len(results),
                'audio_metrics': audio_metrics,
                'response_time': response.get('timestamp', 0) - time.time()
            }
    except Exception as e:
        print(f"Transcription test failed at {volume_pct}%: {e}")
    
    return None

def find_optimal_volume_range(test_audio_file):
    """Find optimal microphone volume range through systematic testing."""
    print("=== Audio Level Optimization Test ===")
    
    # Get current volume as baseline
    original_volume = get_current_mic_volume()
    print(f"Original microphone volume: {original_volume}%")
    
    # Test range from 20% to 100% in steps
    test_volumes = range(30, 101, 10)
    results = []
    
    for volume in test_volumes:
        result = test_transcription_at_volume(volume, test_audio_file)
        if result:
            results.append(result)
            print(f"  {volume}%: {'✓' if result['transcription_success'] else '✗'} "
                  f"RMS={result['audio_metrics']['rms_level']:.4f} "
                  f"Peak={result['audio_metrics']['peak_level']:.3f}")
    
    # Restore original volume
    if original_volume:
        set_mic_volume(original_volume)
        print(f"Restored original volume: {original_volume}%")
    
    # Analyze results
    successful_volumes = [r for r in results if r['transcription_success']]
    
    if successful_volumes:
        optimal_range = {
            'min_volume': min(r['volume_pct'] for r in successful_volumes),
            'max_volume': max(r['volume_pct'] for r in successful_volumes),
            'recommended': successful_volumes[len(successful_volumes)//2]['volume_pct']  # Middle value
        }
        
        print(f"\n=== Optimal Volume Range Found ===")
        print(f"Working range: {optimal_range['min_volume']}% - {optimal_range['max_volume']}%")
        print(f"Recommended: {optimal_range['recommended']}%")
        
        # Save results
        with open('/tmp/audio_level_test_results.json', 'w') as f:
            json.dump({
                'optimal_range': optimal_range,
                'test_results': results,
                'original_volume': original_volume
            }, f, indent=2)
        
        return optimal_range
    else:
        print("No successful transcriptions found - audio may be too quiet or system issues")
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage: audio_level_test.py <audio_file.wav>")
        print("Example: audio_level_test.py /tmp/recorded_audio_test.wav")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    if not os.path.exists(audio_file):
        print(f"Audio file not found: {audio_file}")
        sys.exit(1)
    
    find_optimal_volume_range(audio_file)

if __name__ == "__main__":
    main()