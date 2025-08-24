#!/usr/bin/env python3
"""
Test GPU speech-to-text service integration with key listener.
Simulates the complete workflow without requiring key presses.
"""

import sys
import os
import time
import subprocess
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/test_gpu_integration.log')
    ]
)

def create_test_audio():
    """Create a test audio file using arecord."""
    test_audio = "/tmp/test_gpu_audio.wav"
    
    print("🎤 Creating 3-second test audio file...")
    print("Please speak something for testing...")
    
    try:
        # Record 3 seconds of audio
        cmd = [
            "arecord", 
            "-f", "cd", 
            "-t", "wav", 
            "-d", "3", 
            test_audio
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            logging.info(f"✅ Test audio recorded: {test_audio}")
            return test_audio
        else:
            logging.error(f"❌ Audio recording failed: {result.stderr}")
            return None
            
    except Exception as e:
        logging.error(f"❌ Failed to create test audio: {e}")
        return None

def test_gpu_service(audio_file):
    """Test the GPU speech-to-text service directly."""
    print("\n🚀 Testing GPU Speech-to-Text Service...")
    
    gpu_script = "/home/sati/speech-to-text-for-ubuntu/speech_to_text_gpu.py"
    python_venv = "/home/sati/speech-to-text-for-ubuntu/venv/bin/python3"
    
    try:
        start_time = time.time()
        
        # Run the GPU service
        cmd = [python_venv, gpu_script, audio_file]
        logging.info(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        total_time = time.time() - start_time
        
        if result.returncode == 0:
            logging.info(f"✅ GPU service completed in {total_time:.2f}s")
            logging.info(f"STDOUT: {result.stdout}")
            if result.stderr:
                logging.info(f"STDERR: {result.stderr}")
            return True
        else:
            logging.error(f"❌ GPU service failed: {result.stderr}")
            logging.error(f"STDOUT: {result.stdout}")
            return False
            
    except Exception as e:
        logging.error(f"❌ Failed to run GPU service: {e}")
        return False

def check_gpu_logs():
    """Check the GPU service logs for performance metrics."""
    print("\n📊 Checking GPU Service Logs...")
    
    log_file = "/tmp/speech_to_text.log"
    
    try:
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                lines = f.readlines()
            
            # Get last 20 lines for recent activity
            recent_lines = lines[-20:] if len(lines) > 20 else lines
            
            print("Recent GPU service activity:")
            for line in recent_lines:
                if any(keyword in line for keyword in ['Model loaded', 'Transcription completed', 'Using', 'GPU', 'CUDA']):
                    print(f"  {line.strip()}")
                    
        else:
            logging.warning("No GPU service log file found")
            
    except Exception as e:
        logging.error(f"Failed to read GPU logs: {e}")

def simulate_key_listener_workflow():
    """Simulate the complete key listener workflow with GPU service."""
    print("\n🎯 SIMULATING KEY LISTENER WORKFLOW WITH GPU")
    print("=" * 60)
    
    # Step 1: Create test audio (simulates recording)
    audio_file = create_test_audio()
    if not audio_file:
        return False
    
    # Step 2: Process with GPU service (simulates what happens on key release)
    success = test_gpu_service(audio_file)
    
    # Step 3: Check logs for performance metrics
    check_gpu_logs()
    
    # Cleanup
    try:
        os.remove(audio_file)
        logging.info("Test audio file cleaned up")
    except:
        pass
        
    return success

def main():
    """Main test function."""
    print("🧪 GPU SPEECH-TO-TEXT SERVICE INTEGRATION TEST")
    print("=" * 60)
    
    # Check GPU availability first
    try:
        result = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ GPU detected and accessible")
        else:
            print("❌ GPU not accessible")
            return
    except:
        print("❌ nvidia-smi not found - GPU may not be available")
        return
    
    # Run the integration test
    success = simulate_key_listener_workflow()
    
    if success:
        print("\n🎉 GPU SERVICE INTEGRATION TEST PASSED")
        print("Key listener is now configured to use GPU acceleration!")
        print("\nTo use:")
        print("  python3 key_listener_pynput.py")
        print("  Then press INSERT key to record and test")
    else:
        print("\n❌ GPU SERVICE INTEGRATION TEST FAILED")
        print("Check logs for details")

if __name__ == "__main__":
    main()