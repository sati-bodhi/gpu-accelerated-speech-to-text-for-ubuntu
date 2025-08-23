#!/usr/bin/env python3
"""
Docker-optimized GPU-accelerated speech-to-text using faster-whisper.
Designed to run in CUDA 12.3+ container.
"""

import sys
import time
import os
import torch
from faster_whisper import WhisperModel
import soundfile as sf
import numpy as np

def check_gpu():
    """Check GPU availability and info"""
    cuda_available = torch.cuda.is_available()
    print(f"CUDA available: {cuda_available}")
    
    if cuda_available:
        gpu_count = torch.cuda.device_count()
        print(f"GPU count: {gpu_count}")
        for i in range(gpu_count):
            gpu_name = torch.cuda.get_device_name(i)
            print(f"GPU {i}: {gpu_name}")
        
        # Check memory
        torch.cuda.empty_cache()
        memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        print(f"GPU memory: {memory:.1f} GB")
    
    return cuda_available

def load_audio(file_path):
    """Load audio file"""
    if not os.path.exists(file_path):
        print(f"Error: Audio file not found: {file_path}")
        return None
    
    try:
        audio, sample_rate = sf.read(file_path)
        
        # Convert to float32
        audio = audio.astype(np.float32)
        
        # Convert stereo to mono if needed
        if len(audio.shape) > 1:
            audio = np.mean(audio, axis=1)
        
        print(f"Audio loaded: {file_path}")
        print(f"Duration: {len(audio)/sample_rate:.2f}s, Sample rate: {sample_rate}Hz")
        
        return audio
        
    except Exception as e:
        print(f"Error loading audio: {e}")
        return None

def transcribe_with_gpu(audio, model_size="medium.en"):
    """Transcribe using GPU acceleration"""
    start_time = time.time()
    
    try:
        print(f"Loading {model_size} model on GPU...")
        model = WhisperModel(
            model_size, 
            device="cuda", 
            compute_type="float16",
            download_root="/app/models"
        )
        
        load_time = time.time() - start_time
        print(f"Model loaded in {load_time:.2f}s")
        
        print("Starting GPU transcription...")
        transcribe_start = time.time()
        
        segments, info = model.transcribe(
            audio,
            language="en",
            beam_size=5,
            best_of=5,
            temperature=0,
            vad_filter=True,
            vad_parameters=dict(
                threshold=0.5,
                min_silence_duration_ms=300,
                min_speech_duration_ms=200
            )
        )
        
        # Collect results
        results = []
        for segment in segments:
            text = segment.text.strip()
            if text:
                results.append(text)
                print(f"[{segment.start:.1f}s-{segment.end:.1f}s] {text}")
        
        transcribe_time = time.time() - transcribe_start
        total_time = time.time() - start_time
        
        print(f"\n=== GPU Transcription Results ===")
        print(f"Model: {model_size}")
        print(f"Language: {info.language}")
        print(f"Duration: {info.duration:.2f}s")
        print(f"Segments: {len(results)}")
        print(f"Load time: {load_time:.2f}s")
        print(f"Transcribe time: {transcribe_time:.2f}s") 
        print(f"Total time: {total_time:.2f}s")
        print(f"Speed: {info.duration/transcribe_time:.1f}x realtime")
        
        return results
        
    except Exception as e:
        print(f"GPU transcription failed: {e}")
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 speech_to_text_docker.py <audio_file>")
        print("Example: python3 speech_to_text_docker.py /audio/test.wav")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    
    print("=== Docker GPU Speech-to-Text ===")
    
    # Check GPU
    gpu_available = check_gpu()
    
    if not gpu_available:
        print("❌ No GPU available - this container is designed for GPU use")
        sys.exit(1)
    
    # Load audio
    audio = load_audio(audio_file)
    if audio is None:
        sys.exit(1)
    
    # Transcribe
    results = transcribe_with_gpu(audio)
    
    if results:
        print(f"\n=== Final Transcription ===")
        full_text = " ".join(results)
        print(full_text)
        
        # Save to file if requested
        if len(sys.argv) > 2 and sys.argv[2] == "--save":
            output_file = audio_file.replace('.wav', '_transcription.txt')
            with open(output_file, 'w') as f:
                f.write(full_text)
            print(f"Transcription saved to: {output_file}")
    else:
        print("❌ Transcription failed")
        sys.exit(1)

if __name__ == "__main__":
    main()