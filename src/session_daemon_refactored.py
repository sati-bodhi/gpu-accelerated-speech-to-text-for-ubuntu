#!/usr/bin/env python3
"""
Refactored Session-Based Speech Daemon

Clean, modular architecture using separated services for:
- Audio preprocessing (AudioPreprocessor)
- Model management (ModelManager) 
- Session coordination (SessionCoordinator)
- Text output (TextOutputManager)

This daemon now serves as a thin orchestration layer.
"""

import os
import sys
import time
import json
import logging
import signal
from pathlib import Path
from typing import Optional, Dict, Any

# Import our modular services
from audio_processor import AudioPreprocessor
from speech_engine import SpeechEngine
from session_coordinator import SessionCoordinator, SessionTimeoutMonitor
from text_output import TextOutputManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/session_daemon.log')
    ]
)


class SessionSpeechDaemon:
    """
    Refactored session-aware speech daemon with modular architecture.
    
    This daemon now acts as a thin coordination layer orchestrating
    specialized services for different concerns.
    """
    
    def __init__(self, session_timeout: int = 600):
        self.logger = logging.getLogger(__name__)
        
        # Initialize modular services
        self.audio_processor = AudioPreprocessor(enable_debug=True)
        self.speech_engine = SpeechEngine(model_size="large-v3", vad_threshold=0.16)
        self.session_coordinator = SessionCoordinator(session_timeout=session_timeout)
        self.text_output = TextOutputManager()
        
        # Safety mechanism for infinite loop detection
        self.request_failure_count = {}
        self.max_request_failures = 3
        self.shutdown_requested = False
        
        # IPC directories
        self.request_dir = Path("/tmp/speech_session_requests")
        self.response_dir = Path("/tmp/speech_session_responses")
        
        self._setup_ipc_directories()
        
        # Start session timeout monitoring
        self.timeout_monitor = SessionTimeoutMonitor(self.session_coordinator)
        self.timeout_monitor.start_monitoring()
        
        # Update status with all service information
        self._update_status()
        
        self.logger.info("Modular session speech daemon initialized")
        self.logger.info(f"Services: Audio={type(self.audio_processor).__name__}, "
                        f"Speech={type(self.speech_engine).__name__}, "
                        f"Session={type(self.session_coordinator).__name__}, "
                        f"Output={type(self.text_output).__name__}")
    
    def _setup_ipc_directories(self):
        """Set up IPC directories for request/response communication."""
        try:
            self.request_dir.mkdir(exist_ok=True)
            self.response_dir.mkdir(exist_ok=True)
            self.logger.info("IPC directories ready")
        except Exception as e:
            self.logger.error(f"IPC setup failed: {e}")
            raise
    
    def _update_status(self):
        """Update daemon status using session coordinator."""
        try:
            # Gather status from all services
            additional_data = {
                "model_loaded": self.speech_engine.is_model_loaded,
                "device": self.speech_engine.device,
                "model_size": self.speech_engine.model_size,
                "vad_threshold": self.speech_engine.get_vad_parameters().threshold,
                "audio_debug_enabled": self.audio_processor.enable_debug,
                "text_output_available": self.text_output.is_output_available()
            }
            
            self.session_coordinator.update_status_file(additional_data)
            
        except Exception as e:
            self.logger.warning(f"Status update failed: {e}")
    
    def transcribe_audio_file(self, audio_file: str) -> Dict[str, Any]:
        """
        Complete audio processing pipeline using modular services.
        
        Returns:
            Dict with transcription results and processing metadata
        """
        # Update activity to extend session
        self.session_coordinator.update_activity()
        self.session_coordinator.set_processing(True)
        
        try:
            # Step 1: Audio preprocessing
            self.logger.info("Processing audio with noise cancelling...")
            processed_audio = self.audio_processor.process_audio_file(audio_file)
            
            # Check if audio has content
            if not processed_audio.analysis.has_content:
                self.logger.info("Skipping transcription - no audio content detected")
                return {
                    "success": True,
                    "results": [],
                    "reason": "no_content",
                    "audio_analysis": processed_audio.analysis.__dict__
                }
            
            # Step 2: Speech engine transcription
            self.logger.info("Transcribing with optimized VAD parameters...")
            transcription_result = self.speech_engine.transcribe_audio(
                processed_audio.audio, 
                processed_audio.sample_rate
            )
            
            if not transcription_result.success:
                return {
                    "success": False,
                    "results": [],
                    "error": transcription_result.error_message,
                    "audio_analysis": processed_audio.analysis.__dict__
                }
            
            # Step 3: Text output
            if transcription_result.segments:
                self.logger.info(f"Typing {len(transcription_result.segments)} segments...")
                typed_count = self.text_output.type_transcription_results(transcription_result.segments)
                
                if typed_count == 0:
                    self.logger.warning("Failed to type any transcription results")
            else:
                self.logger.info("No transcription segments to output")
            
            # Log session continuation
            expiry_time = time.strftime('%H:%M:%S', 
                                     time.localtime(self.session_coordinator.get_session_expiry_time()))
            self.logger.info(f"Session will stay active until {expiry_time}")
            
            return {
                "success": True,
                "results": transcription_result.segments,
                "processing_time": transcription_result.processing_time,
                "device_used": transcription_result.device_used,
                "audio_analysis": processed_audio.analysis.__dict__,
                "preprocessing_applied": processed_audio.preprocessing_applied,
                "debug_file": processed_audio.debug_file
            }
            
        except Exception as e:
            self.logger.error(f"Transcription pipeline failed: {e}")
            return {
                "success": False,
                "results": [],
                "error": str(e)
            }
        finally:
            self.session_coordinator.set_processing(False)
            self._update_status()
    
    def process_request(self, request_file: Path):
        """Process a single transcription request using modular services."""
        try:
            with open(request_file, 'r') as f:
                request = json.load(f)
            
            request_id = request.get('id')
            request_type = request.get('type', 'transcribe')
            
            # Safety check: detect infinite loops from repeated request failures
            if request_id in self.request_failure_count:
                self.request_failure_count[request_id] += 1
                if self.request_failure_count[request_id] > self.max_request_failures:
                    self.logger.error(f"Request {request_id} failed {self.max_request_failures} times - initiating emergency shutdown to prevent infinite loop")
                    self.shutdown_requested = True
                    return
            else:
                self.request_failure_count[request_id] = 0
            
            self.logger.info(f"Processing {request_type} request {request_id}")
            
            # Handle ping requests for responsiveness testing
            if request_type == 'ping':
                status = self.session_coordinator.get_session_status()
                response = {
                    'id': request_id,
                    'type': 'pong',
                    'timestamp': time.time(),
                    'device': self.speech_engine.device,
                    'session_active': status.active,
                    'model_loaded': self.speech_engine.is_model_loaded,
                    'uptime': status.uptime
                }
            else:
                # Handle transcription requests
                audio_file = request.get('audio_file')
                if not audio_file:
                    raise ValueError("No audio_file specified in request")
                
                result = self.transcribe_audio_file(audio_file)
                
                response = {
                    'id': request_id,
                    'results': result.get('results', []),
                    'timestamp': time.time(),
                    'device': self.speech_engine.device,
                    'session_active': self.session_coordinator.is_session_active(),
                    'success': result.get('success', False),
                    'processing_time': result.get('processing_time', 0.0),
                    'metadata': {
                        'audio_analysis': result.get('audio_analysis'),
                        'preprocessing_applied': result.get('preprocessing_applied'),
                        'debug_file': result.get('debug_file')
                    }
                }
                
                if not result.get('success'):
                    response['error'] = result.get('error', 'Unknown error')
            
            # Write response
            response_file = self.response_dir / f"{request_id}.json"
            with open(response_file, 'w') as f:
                json.dump(response, f)
            
            # Clean up request
            request_file.unlink()
            
            # Clear failure count on successful completion
            if request_id in self.request_failure_count:
                del self.request_failure_count[request_id]
            
            self.logger.info(f"Request {request_id} completed successfully")
            
        except Exception as e:
            # Track failure for infinite loop detection
            if request_id and request_id not in self.request_failure_count:
                self.request_failure_count[request_id] = 1
            elif request_id:
                self.request_failure_count[request_id] += 1
                
            self.logger.error(f"Request processing failed: {e} (failure #{self.request_failure_count.get(request_id, 1)})")
            
            # Try to write error response
            try:
                if 'request_id' in locals():
                    error_response = {
                        'id': request_id,
                        'success': False,
                        'error': str(e),
                        'timestamp': time.time()
                    }
                    
                    response_file = self.response_dir / f"{request_id}.json"
                    with open(response_file, 'w') as f:
                        json.dump(error_response, f)
            except Exception:
                pass  # Best effort error response
    
    def shutdown(self):
        """Graceful shutdown of all services."""
        self.logger.info("Shutting down session daemon...")
        
        # Request shutdown from session coordinator
        self.session_coordinator.request_shutdown()
        
        # Release speech engine resources
        if self.speech_engine.is_model_loaded:
            self.speech_engine.release_model()
        
        # Clean up session files
        self.session_coordinator.cleanup_session_files()
        
        self.logger.info("Modular session daemon shutdown complete")
    
    def run(self):
        """Main daemon loop with modular service coordination."""
        self.logger.info("Modular session daemon started - waiting for requests...")
        
        while self.session_coordinator.is_session_active() and not self.shutdown_requested:
            try:
                # Check for new requests
                request_files = list(self.request_dir.glob("*.json"))
                
                for request_file in request_files:
                    if not self.session_coordinator.is_session_active() or self.shutdown_requested:
                        break
                    
                    self.process_request(request_file)
                    
                    # Additional safety check after processing
                    if self.shutdown_requested:
                        self.logger.error("Emergency shutdown triggered - terminating daemon")
                        break
                
                # Brief pause between checks
                time.sleep(0.1)
                
            except KeyboardInterrupt:
                self.logger.info("Received shutdown signal")
                break
            except Exception as e:
                self.logger.error(f"Daemon loop error: {e}")
                time.sleep(1)
        
        # Shutdown
        self.shutdown()


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    global daemon
    if daemon:
        daemon.shutdown()
    sys.exit(0)


def main():
    """Main daemon entry point."""
    global daemon
    
    # Check if daemon is already running
    from session_coordinator import check_existing_session
    
    existing_session = check_existing_session()
    if existing_session and existing_session.get('responsive'):
        logging.info(f"Session daemon already running (PID: {existing_session['pid']}) - exiting")
        sys.exit(0)
    
    # Set up signal handling
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Parse session timeout argument
    session_timeout = 600  # 10 minutes default
    if len(sys.argv) > 1:
        try:
            session_timeout = int(sys.argv[1])
        except ValueError:
            logging.warning("Invalid timeout argument, using default 10 minutes")
    
    # Create and start modular daemon
    logging.info(f"Starting Modular Session Speech Daemon (timeout: {session_timeout/60:.1f}min)...")
    daemon = SessionSpeechDaemon(session_timeout=session_timeout)
    daemon.run()


if __name__ == "__main__":
    daemon = None
    main()