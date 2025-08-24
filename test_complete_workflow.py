#!/usr/bin/env python3
"""
Complete workflow test: Listener → Daemon → Processing
"""

import sys
import os
import time
import subprocess
sys.path.append('/home/sati/speech-to-text-for-ubuntu')

from key_listener_pynput import is_daemon_running, process_with_daemon, process_with_standalone

def simulate_listener_workflow():
    """Simulate the complete listener workflow"""
    print("🎯 SIMULATING COMPLETE LISTENER WORKFLOW")
    print("=" * 60)
    
    # Simulate audio file (using existing test audio)
    audio_file = "/tmp/recorded_audio.wav"
    if not os.path.exists(audio_file):
        print("❌ No test audio file found")
        return
    
    print(f"🎵 Simulating INSERT key release with: {audio_file}")
    
    # This is what stop_recording_and_process() does:
    print("\n1️⃣ Checking daemon status...")
    daemon_running = is_daemon_running()
    
    if daemon_running:
        print("✅ Daemon detected - using fast processing")
        start_time = time.time()
        success = process_with_daemon(audio_file)
        total_time = time.time() - start_time
        method = "DAEMON"
    else:
        print("📁 No daemon - using standalone fallback")  
        start_time = time.time()
        success = process_with_standalone(audio_file)
        total_time = time.time() - start_time
        method = "STANDALONE"
    
    print(f"\n2️⃣ Processing completed:")
    print(f"   Method: {method}")
    print(f"   Success: {'✅' if success else '❌'}")
    print(f"   Time: {total_time:.1f}s")
    
    print("\n3️⃣ In real workflow:")
    print("   - Audio would be cleaned up")
    print("   - Corrected text would be typed via pyautogui")
    print("   - User sees result immediately")

def test_refresh_workflow():
    """Test the refresh workflow"""
    print("\n" + "=" * 60)
    print("🔄 TESTING REFRESH WORKFLOW")
    print("=" * 60)
    
    if not is_daemon_running():
        print("❌ No daemon running - can't test refresh")
        return
        
    print("1️⃣ Sending refresh signal...")
    signal_file = "/tmp/speech_daemon_refresh_signal"
    with open(signal_file, 'w') as f:
        f.write(str(int(time.time())))
    
    print("2️⃣ Refresh signal sent - daemon will detect in background")
    print("3️⃣ In real workflow:")
    print("   - User types /refresh-stt-context")
    print("   - Daemon captures new context (~30s)")
    print("   - New correction session established")
    print("   - Next corrections use fresh context")

def show_complete_architecture():
    """Show the complete architecture"""
    print("\n" + "=" * 60)
    print("🏗️ COMPLETE ARCHITECTURE")
    print("=" * 60)
    
    daemon_status = "RUNNING" if is_daemon_running() else "STOPPED"
    
    print(f"""
🎛️ CURRENT STATUS:
   Daemon: {daemon_status}
   
📋 FULL WORKFLOW:

┌─────────────────────────────────────────────────────┐
│ USER INTERACTION                                    │
├─────────────────────────────────────────────────────┤
│ 1. Press INSERT key (start recording)              │
│ 2. Speak into microphone                           │
│ 3. Release INSERT key (stop & process)             │
└─────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────┐
│ KEY LISTENER (key_listener_pynput.py)              │
├─────────────────────────────────────────────────────┤
│ 1. Records audio to timestamped file               │
│ 2. Checks if daemon is running                     │
│ 3. Routes to daemon OR standalone                  │
└─────────────────────────────────────────────────────┘
                            │
                    ┌───────┴────────┐
                    │                │
┌─────────────────────────┐    ┌─────────────────────────┐
│ DAEMON PATH (FAST)      │    │ STANDALONE (FALLBACK)  │
├─────────────────────────┤    ├─────────────────────────┤
│ • File request/response │    │ • Direct script call   │
│ • Persistent Whisper   │    │ • Cold-load Whisper    │
│ • Session-resume Claude │    │ • Limited context      │
│ • ~6s processing        │    │ • ~10-15s processing    │
└─────────────────────────┘    └─────────────────────────┘
                    │                │
                    └───────┬────────┘
                            │
┌─────────────────────────────────────────────────────┐
│ OUTPUT                                              │
├─────────────────────────────────────────────────────┤
│ • Corrected text typed via pyautogui               │
│ • Audio file cleaned up                            │
│ • Process complete                                  │
└─────────────────────────────────────────────────────┘

🔄 REFRESH MECHANISM:
   User types: /refresh-stt-context
   → Creates signal file
   → Daemon detects and refreshes context
   → New session ready for better corrections
""")

if __name__ == "__main__":
    simulate_listener_workflow()
    test_refresh_workflow() 
    show_complete_architecture()