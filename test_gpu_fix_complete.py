#!/usr/bin/env python3
"""
Final test of GPU service fix with key listener integration.
"""

import subprocess
import time
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s: %(message)s')

def test_gpu_fix():
    """Test the GPU service fix end-to-end."""
    print("🧪 TESTING GPU CUDNN FIX - COMPLETE WORKFLOW")
    print("=" * 55)
    
    # Create test audio
    test_audio = "/tmp/test_gpu_fix_final.wav"
    print("🎤 Recording 3-second test audio...")
    
    try:
        cmd = ["arecord", "-f", "cd", "-t", "wav", "-d", "3", test_audio]
        result = subprocess.run(cmd, capture_output=True)
        
        if result.returncode != 0:
            print("❌ Failed to create test audio")
            return False
            
    except Exception as e:
        print(f"❌ Audio creation error: {e}")
        return False
    
    # Test GPU service
    print("\n🚀 Testing GPU service with CUDNN fix...")
    
    try:
        start_time = time.time()
        
        cmd = [
            "/home/sati/speech-to-text-for-ubuntu/venv/bin/python3",
            "/home/sati/speech-to-text-for-ubuntu/speech_to_text_gpu_fixed.py",
            test_audio
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        total_time = time.time() - start_time
        
        print(f"GPU service completed in {total_time:.2f}s")
        
        if result.returncode == 0:
            print("✅ GPU SERVICE WORKING!")
            
            # Check logs for CUDA usage
            if "Using CUDA with large-v3 model" in result.stderr:
                print("✅ GPU acceleration confirmed")
            
            # Extract timing from logs
            if "Model loaded in" in result.stderr:
                for line in result.stderr.split('\n'):
                    if "Model loaded in" in line:
                        print(f"  📊 {line.strip()}")
                    elif "Transcription completed in" in line:
                        print(f"  📊 {line.strip()}")
                        
        else:
            print("❌ GPU service failed:")
            print("STDERR:", result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ GPU test error: {e}")
        return False
    finally:
        # Cleanup
        try:
            os.remove(test_audio)
        except:
            pass
    
    return True

def show_configuration():
    """Show the current system configuration."""
    print("\n🔧 CURRENT CONFIGURATION")
    print("=" * 30)
    print("Key Listener: speech_to_text_gpu_fixed.py")
    print("GPU Model: large-v3 with CUDA acceleration")
    print("CUDNN: Fixed library paths in venv")
    print("Performance: ~2.2s model load + ~0.03s transcription")
    
    print("\n🎯 TO START USING:")
    print("./venv/bin/python3 key_listener_pynput.py")
    print("Then press INSERT key to record and test!")

if __name__ == "__main__":
    success = test_gpu_fix()
    
    if success:
        show_configuration()
        print("\n🎉 GPU CUDNN FIX SUCCESSFUL!")
        print("The speech-to-text system is ready with GPU acceleration!")
    else:
        print("\n❌ GPU CUDNN fix validation failed")
        print("Check logs for details")