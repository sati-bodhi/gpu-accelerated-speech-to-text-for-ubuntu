#!/usr/bin/env python3
"""
Docker GPU wrapper for speech-to-text using linuxserver/faster-whisper:gpu image.
This script runs transcription in a Docker container with GPU acceleration.
"""

import sys
import os
import subprocess
import json
import time
import logging
import tempfile
import shutil

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/speech_to_text_docker.log')
    ]
)

def test_docker_gpu():
    """Test if Docker and GPU are available"""
    try:
        # Test Docker
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        if result.returncode != 0:
            logging.error("Docker not available")
            return False
        
        # Test GPU in container
        result = subprocess.run([
            'docker', 'run', '--rm', '--gpus', 'all', 
            '--entrypoint', '/bin/bash',
            'lscr.io/linuxserver/faster-whisper:gpu',
            '-c', 'nvidia-smi -L'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 and 'GPU' in result.stdout:
            logging.info(f"GPU available in Docker: {result.stdout.strip()}")
            return True
        else:
            logging.error("GPU not available in Docker")
            return False
            
    except Exception as e:
        logging.error(f"Docker/GPU test failed: {e}")
        return False

def transcribe_with_docker(audio_file, model="large-v3"):
    """Transcribe audio using Docker GPU container"""
    
    if not os.path.exists(audio_file):
        logging.error(f"Audio file not found: {audio_file}")
        return None
    
    # Create a Python script to run inside the container
    script_content = f'''
import sys
import time
from faster_whisper import WhisperModel

audio_file = "/audio/{os.path.basename(audio_file)}"

print(f"Loading {model} model on GPU...", file=sys.stderr)
start_load = time.time()

# Load model with GPU
model = WhisperModel("{model}", device="cuda", compute_type="float16")
print(f"Model loaded in {{time.time() - start_load:.1f}}s", file=sys.stderr)

# Transcribe directly from file
print(f"Transcribing {{audio_file}}...", file=sys.stderr)
start_trans = time.time()
segments, info = model.transcribe(
    audio_file,
    language="en",
    beam_size=5,
    best_of=5,
    vad_filter=False
)

# Collect results
results = []
for segment in segments:
    text = segment.text.strip()
    if text:
        results.append(text)

trans_time = time.time() - start_trans
print(f"Transcription completed in {{trans_time:.1f}}s", file=sys.stderr)
print(f"Detected language: {{info.language}} with probability {{info.language_probability:.2f}}", file=sys.stderr)

# Output the transcript
print(" ".join(results))
'''
    
    # Create temporary script file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        script_file = f.name
        f.write(script_content)
    
    try:
        # Get directory and filename
        audio_dir = os.path.dirname(os.path.abspath(audio_file))
        audio_name = os.path.basename(audio_file)
        
        logging.info(f"Running transcription in Docker GPU container with {model} model...")
        
        # Run Docker container with GPU
        cmd = [
            'docker', 'run', '--rm', 
            '--gpus', 'all',
            '-v', f'{audio_dir}:/audio:ro',
            '-v', f'{script_file}:/script.py:ro',
            '--entrypoint', 'python3',
            'lscr.io/linuxserver/faster-whisper:gpu',
            '/script.py'
        ]
        
        # Script already has the correct path
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            transcript = result.stdout.strip()
            logging.info(f"Transcription successful: {transcript[:100]}...")
            return transcript
        else:
            logging.error(f"Docker transcription failed: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        logging.error("Docker transcription timed out")
        return None
    except Exception as e:
        logging.error(f"Docker transcription error: {e}")
        return None
    finally:
        # Cleanup
        if os.path.exists(script_file):
            os.remove(script_file)

def type_text(text):
    """Type text using pyautogui"""
    try:
        import pyautogui
        logging.info(f"Typing: {text}")
        pyautogui.typewrite(text + ' ')
    except Exception as e:
        logging.error(f"Failed to type text: {e}")

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python speech_to_text_docker_gpu.py <audio_file> [model]")
        print("Models: tiny, base, small, medium, large-v3 (default)")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    model = sys.argv[2] if len(sys.argv) > 2 else "large-v3"
    
    # Test Docker GPU first
    if not test_docker_gpu():
        logging.error("Docker GPU not available, falling back to CPU script")
        # Fall back to CPU version
        import subprocess
        subprocess.run([sys.executable, "speech_to_text_large.py", audio_file])
        return
    
    # Process with Docker GPU
    logging.info(f"Processing {audio_file} with Docker GPU ({model} model)")
    
    transcript = transcribe_with_docker(audio_file, model)
    
    if transcript:
        type_text(transcript)
        logging.info("Processing completed")
    else:
        logging.error("Transcription failed")
        sys.exit(1)

if __name__ == "__main__":
    main()