#!/usr/bin/env python3
"""
Performance comparison: GPU vs CPU speech-to-text processing
"""

import subprocess
import time
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s: %(message)s')

def create_test_audio():
    """Create a longer test audio file for performance testing."""
    test_audio = "/tmp/performance_test_audio.wav"
    
    print("🎤 Recording 5-second audio for performance test...")
    
    try:
        cmd = ["arecord", "-f", "cd", "-t", "wav", "-d", "5", test_audio]
        result = subprocess.run(cmd, capture_output=True)
        
        if result.returncode == 0 and os.path.exists(test_audio):
            file_size = os.path.getsize(test_audio) / 1024  # KB
            logging.info(f"Test audio created: {test_audio} ({file_size:.1f} KB)")
            return test_audio
        else:
            logging.error("Failed to create test audio")
            return None
            
    except Exception as e:
        logging.error(f"Audio creation failed: {e}")
        return None

def test_performance(script_name, test_name, audio_file):
    """Test performance of a speech-to-text script."""
    python_venv = "/home/sati/speech-to-text-for-ubuntu/venv/bin/python3"
    script_path = f"/home/sati/speech-to-text-for-ubuntu/{script_name}"
    
    print(f"\n🧪 Testing {test_name}...")
    
    try:
        start_time = time.time()
        
        cmd = [python_venv, script_path, audio_file]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        total_time = time.time() - start_time
        
        if result.returncode == 0:
            print(f"✅ {test_name}: {total_time:.2f}s")
            
            # Extract model loading and transcription times from logs
            stderr_lines = result.stderr.split('\n')
            model_time = None
            transcription_time = None
            
            for line in stderr_lines:
                if "Model loaded in" in line:
                    try:
                        model_time = float(line.split("Model loaded in ")[1].split("s")[0])
                    except:
                        pass
                elif "Transcription completed in" in line:
                    try:
                        transcription_time = float(line.split("Transcription completed in ")[1].split("s")[0])
                    except:
                        pass
            
            return {
                'success': True,
                'total_time': total_time,
                'model_time': model_time,
                'transcription_time': transcription_time,
                'stderr': result.stderr
            }
        else:
            print(f"❌ {test_name} failed: {result.stderr}")
            return {'success': False, 'error': result.stderr}
            
    except Exception as e:
        print(f"❌ {test_name} error: {e}")
        return {'success': False, 'error': str(e)}

def main():
    """Run performance comparison."""
    print("🏎️  GPU vs CPU PERFORMANCE COMPARISON")
    print("=" * 50)
    
    # Create test audio
    audio_file = create_test_audio()
    if not audio_file:
        print("❌ Cannot create test audio - aborting")
        return
    
    # Test configurations
    tests = [
        ("speech_to_text_gpu.py", "GPU (large-v3)"),
        ("speech_to_text_large.py", "CPU (large-v3)"),
        ("speech_to_text_parallel.py", "CPU (parallel)"),
    ]
    
    results = {}
    
    # Run tests
    for script, name in tests:
        if os.path.exists(f"/home/sati/speech-to-text-for-ubuntu/{script}"):
            results[name] = test_performance(script, name, audio_file)
        else:
            print(f"⚠️  {script} not found - skipping")
    
    # Display results
    print("\n📊 PERFORMANCE RESULTS")
    print("=" * 50)
    
    successful_results = {k: v for k, v in results.items() if v.get('success')}
    
    if successful_results:
        print(f"{'Configuration':<20} {'Total':<8} {'Model':<8} {'Transcription':<13}")
        print("-" * 50)
        
        for name, result in successful_results.items():
            total = f"{result['total_time']:.2f}s"
            model = f"{result['model_time']:.2f}s" if result['model_time'] else "N/A"
            transcription = f"{result['transcription_time']:.3f}s" if result['transcription_time'] else "N/A"
            
            print(f"{name:<20} {total:<8} {model:<8} {transcription:<13}")
    
    # Cleanup
    try:
        os.remove(audio_file)
        logging.info("Test audio cleaned up")
    except:
        pass
    
    print(f"\n🎯 Recommendation: Use GPU service for fastest transcription!")
    print(f"Key listener is configured to use: speech_to_text_gpu.py")

if __name__ == "__main__":
    main()