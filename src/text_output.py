#!/usr/bin/env python3
"""
Text Output Management Service

Handles text typing, corrections, and output formatting.
Separated from main daemon for focused text output responsibility.
"""

import time
import logging
from typing import List, Optional
from dataclasses import dataclass

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    pyautogui = None


@dataclass
class OutputSettings:
    """Configuration for text output behavior."""
    pause_between_chars: float = 0.02  # 20ms delay between keystrokes
    enable_failsafe: bool = True
    focus_delay: float = 0.05  # Brief delay for window focus stability
    correction_prefix: str = " → "  # Prefix for corrections


class TextOutputManager:
    """
    Service for text output and correction handling.
    
    Responsibilities:
    - Text typing via pyautogui with proper timing
    - Correction output formatting and handling
    - Output settings management and error handling
    - Accessibility and reliability features
    """
    
    def __init__(self, settings: Optional[OutputSettings] = None):
        self.settings = settings or OutputSettings()
        self.logger = logging.getLogger(__name__)
        
        if not PYAUTOGUI_AVAILABLE:
            self.logger.warning("pyautogui not available - text output disabled")
            return
        
        # Configure pyautogui settings
        pyautogui.PAUSE = self.settings.pause_between_chars
        pyautogui.FAILSAFE = self.settings.enable_failsafe
        
        self.logger.info("Text output manager initialized")
    
    def _prepare_for_output(self):
        """Prepare for text output with focus stability."""
        if self.settings.focus_delay > 0:
            time.sleep(self.settings.focus_delay)
    
    def type_text(self, text: str, prepare_focus: bool = True) -> bool:
        """
        Type text using pyautogui with error handling.
        
        Args:
            text: Text to type
            prepare_focus: Whether to add focus delay
            
        Returns:
            True if typing succeeded, False otherwise
        """
        if not PYAUTOGUI_AVAILABLE:
            self.logger.warning(f"Cannot type text (pyautogui unavailable): {text}")
            return False
        
        if not text.strip():
            self.logger.debug("Skipping empty text output")
            return True
        
        try:
            if prepare_focus:
                self._prepare_for_output()
            
            pyautogui.typewrite(text)
            self.logger.info(f"Typed: {text}")
            return True
            
        except Exception as e:
            self.logger.error(f"Text typing failed: {e}")
            return False
    
    def type_transcription_results(self, results: List[str]) -> int:
        """
        Type multiple transcription results with spacing.
        
        Args:
            results: List of transcribed text segments
            
        Returns:
            Number of successfully typed segments
        """
        if not results:
            self.logger.debug("No transcription results to type")
            return 0
        
        successful_outputs = 0
        
        for i, text in enumerate(results):
            # Add space between segments (but not after the last one)
            output_text = text + (' ' if i < len(results) - 1 else '')
            
            if self.type_text(output_text, prepare_focus=(i == 0)):
                successful_outputs += 1
            else:
                self.logger.warning(f"Failed to type segment {i+1}/{len(results)}: {text}")
        
        self.logger.info(f"Typed {successful_outputs}/{len(results)} transcription segments")
        return successful_outputs
    
    def type_correction(self, correction: str) -> bool:
        """
        Type a correction with proper formatting.
        
        Args:
            correction: Corrected text to output
            
        Returns:
            True if correction typing succeeded
        """
        if not correction.strip():
            self.logger.debug("Skipping empty correction")
            return True
        
        # Format correction with prefix
        formatted_correction = f"{self.settings.correction_prefix}{correction}"
        
        success = self.type_text(formatted_correction)
        
        if success:
            self.logger.info(f"Typed correction: {correction}")
        else:
            self.logger.error(f"Failed to type correction: {correction}")
        
        return success
    
    def update_settings(self, new_settings: OutputSettings):
        """Update output settings and reconfigure pyautogui."""
        self.settings = new_settings
        
        if PYAUTOGUI_AVAILABLE:
            pyautogui.PAUSE = self.settings.pause_between_chars
            pyautogui.FAILSAFE = self.settings.enable_failsafe
            
        self.logger.info(f"Output settings updated - pause: {self.settings.pause_between_chars}s")
    
    def get_settings(self) -> OutputSettings:
        """Get current output settings."""
        return self.settings
    
    def test_output(self, test_text: str = "Test output from speech-to-text system") -> bool:
        """
        Test text output functionality.
        
        Args:
            test_text: Text to use for testing
            
        Returns:
            True if test succeeded
        """
        self.logger.info("Testing text output functionality...")
        return self.type_text(test_text)
    
    def is_output_available(self) -> bool:
        """Check if text output is available."""
        return PYAUTOGUI_AVAILABLE
    
    def get_status(self) -> dict:
        """Get text output manager status."""
        return {
            "available": PYAUTOGUI_AVAILABLE,
            "pause_between_chars": self.settings.pause_between_chars,
            "failsafe_enabled": self.settings.enable_failsafe,
            "focus_delay": self.settings.focus_delay,
            "correction_prefix": self.settings.correction_prefix
        }


# Convenience functions for backward compatibility
def type_transcription_results(results: List[str], settings: Optional[OutputSettings] = None) -> int:
    """Standalone function for typing transcription results."""
    manager = TextOutputManager(settings)
    return manager.type_transcription_results(results)


def type_correction(correction: str, settings: Optional[OutputSettings] = None) -> bool:
    """Standalone function for typing corrections."""
    manager = TextOutputManager(settings)
    return manager.type_correction(correction)


if __name__ == "__main__":
    # Test the text output manager
    import sys
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    print("=== Text Output Manager Test ===")
    
    # Create manager with test settings
    test_settings = OutputSettings(
        pause_between_chars=0.01,  # Faster for testing
        focus_delay=0.1
    )
    
    manager = TextOutputManager(test_settings)
    
    print(f"Output available: {manager.is_output_available()}")
    print(f"Status: {manager.get_status()}")
    
    if len(sys.argv) > 1:
        # Type provided text
        test_text = " ".join(sys.argv[1:])
        print(f"Typing test text: {test_text}")
        
        # Give user time to focus desired window
        print("Focus target window... typing in 3 seconds...")
        time.sleep(3)
        
        success = manager.type_text(test_text)
        print(f"Typing result: {'Success' if success else 'Failed'}")
    else:
        # Test transcription results
        test_results = ["Hello", "world", "from", "speech", "to", "text"]
        print(f"Testing transcription results: {test_results}")
        
        print("Focus target window... typing in 3 seconds...")
        time.sleep(3)
        
        typed_count = manager.type_transcription_results(test_results)
        print(f"Typed {typed_count}/{len(test_results)} segments")
        
        # Test correction
        time.sleep(1)
        correction_success = manager.type_correction("corrected text")
        print(f"Correction typing: {'Success' if correction_success else 'Failed'}")