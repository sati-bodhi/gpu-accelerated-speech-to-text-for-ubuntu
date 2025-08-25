#!/usr/bin/env python3
"""
Simple script to type corrected text with the same reliability as the session daemon
"""
import sys
import time
import pyautogui

def main():
    if len(sys.argv) < 2:
        print("Usage: type_correction.py '<corrected text>'")
        sys.exit(1)
    
    corrected_text = sys.argv[1]
    
    # Use same pyautogui settings as session daemon
    pyautogui.PAUSE = 0.02  # 20ms delay between keystrokes
    pyautogui.FAILSAFE = True  # Enable failsafe
    
    try:
        # Brief delay for window focus stability
        time.sleep(0.05)
        
        # Type the correction with a clear prefix
        output_text = f" → {corrected_text}"
        pyautogui.typewrite(output_text)
        
        print(f"Typed correction: {corrected_text}")
        
    except Exception as e:
        print(f"Typing failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()