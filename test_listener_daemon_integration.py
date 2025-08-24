#!/usr/bin/env python3
"""
Test script for daemon-aware listener integration
"""

import sys
import os
sys.path.append('/home/sati/speech-to-text-for-ubuntu')

from key_listener_pynput import is_daemon_running, process_with_daemon, process_with_standalone

def test_daemon_detection():
    """Test daemon detection functionality"""
    print("🧪 Testing daemon detection...")
    
    daemon_status = is_daemon_running()
    print(f"Daemon running: {daemon_status}")
    
    if daemon_status:
        print("✅ Daemon detected - can use fast processing")
    else:
        print("📁 No daemon - will use standalone fallback")
    
    return daemon_status

def test_processing_methods():
    """Test both processing methods"""
    # Use existing test audio if available
    test_audio = "/tmp/recorded_audio.wav"
    if not os.path.exists(test_audio):
        print(f"⚠️ Test audio not found: {test_audio}")
        print("Run a real recording first to test processing")
        return
    
    print(f"🎵 Testing with audio file: {test_audio}")
    
    daemon_running = is_daemon_running()
    
    if daemon_running:
        print("\n🚀 Testing daemon processing...")
        daemon_success = process_with_daemon(test_audio)
        print(f"Daemon processing: {'✅ Success' if daemon_success else '❌ Failed'}")
    else:
        print("\n📁 Testing standalone processing...")
        standalone_success = process_with_standalone(test_audio)
        print(f"Standalone processing: {'✅ Success' if standalone_success else '❌ Failed'}")

def test_architecture():
    """Test the overall architecture"""
    print("\n" + "="*60)
    print("🏗️ LISTENER-DAEMON INTEGRATION TEST")
    print("="*60)
    
    # Test daemon detection
    daemon_running = test_daemon_detection()
    
    # Test processing methods
    test_processing_methods()
    
    # Show expected workflow
    print(f"\n📋 EXPECTED WORKFLOW:")
    if daemon_running:
        print("1. User presses INSERT → records audio")
        print("2. Releases INSERT → listener detects daemon")
        print("3. Sends file request to daemon")
        print("4. Daemon processes with persistent model + session")
        print("5. ~6 second total processing time")
        print("6. Results typed via pyautogui")
    else:
        print("1. User presses INSERT → records audio")
        print("2. Releases INSERT → no daemon detected")
        print("3. Falls back to standalone script")
        print("4. Cold-loads model + uses limited context")
        print("5. ~10-15 second total processing time")
        print("6. Results typed via pyautogui")
    
    print(f"\n💡 To test daemon: Run 'python speech_daemon.py' then test listener")

if __name__ == "__main__":
    test_architecture()