#!/usr/bin/env python3
"""
Session Coordination Service

Manages session lifecycle, activity tracking, and timeout handling.
Separated from main daemon for focused session management.
"""

import os
import time
import json
import threading
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class SessionStatus:
    """Current session state information."""
    active: bool
    last_activity: float
    session_timeout: float
    processing: bool
    pid: int
    uptime: float


class SessionCoordinator:
    """
    Service for session lifecycle and activity management.
    
    Responsibilities:
    - Activity tracking and timeout monitoring
    - Session state persistence and IPC
    - Single-instance protection via PID files
    - Graceful shutdown coordination
    """
    
    def __init__(self, session_timeout: int = 600):  # 10 minutes default
        self.session_timeout = session_timeout
        self.last_activity = time.time()
        self.start_time = time.time()
        self.processing = False
        self.shutdown_requested = False
        self.activity_lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
        
        # IPC and persistence paths
        self.session_file = Path("/tmp/session_daemon_active")
        self.status_file = Path("/tmp/session_daemon_status.json")
        self.pid_file = Path("/tmp/session_daemon.pid")
        
        self._setup_session_files()
        self.logger.info(f"Session coordinator initialized (timeout: {session_timeout}s)")
    
    def _setup_session_files(self):
        """Initialize session persistence files."""
        try:
            # Create PID file for single-instance protection
            with open(self.pid_file, 'w') as f:
                f.write(str(os.getpid()))
            
            # Create session marker file
            with open(self.session_file, 'w') as f:
                json.dump({
                    "started": self.start_time,
                    "pid": os.getpid(),
                    "timeout": self.session_timeout
                }, f)
            
            self.logger.info(f"Session files initialized (PID: {os.getpid()})")
            
        except Exception as e:
            self.logger.warning(f"Session file setup failed: {e}")
    
    def update_activity(self):
        """Update last activity timestamp to extend session."""
        with self.activity_lock:
            self.last_activity = time.time()
            self.logger.debug("Session activity updated")
    
    def set_processing(self, processing: bool):
        """Update processing state for status reporting."""
        self.processing = processing
        if processing:
            self.update_activity()  # Processing counts as activity
    
    def get_inactive_time(self) -> float:
        """Get seconds since last activity."""
        with self.activity_lock:
            return time.time() - self.last_activity
    
    def should_shutdown_due_to_timeout(self) -> bool:
        """Check if session should shutdown due to inactivity."""
        if self.shutdown_requested:
            return True
            
        inactive_time = self.get_inactive_time()
        return inactive_time > self.session_timeout
    
    def get_session_status(self) -> SessionStatus:
        """Get current session status for monitoring."""
        with self.activity_lock:
            return SessionStatus(
                active=not self.shutdown_requested,
                last_activity=self.last_activity,
                session_timeout=self.session_timeout,
                processing=self.processing,
                pid=os.getpid(),
                uptime=time.time() - self.start_time
            )
    
    def update_status_file(self, additional_data: Optional[Dict[str, Any]] = None):
        """Update persistent status file for external monitoring."""
        try:
            status = self.get_session_status()
            
            status_data = {
                "active": status.active,
                "processing": status.processing,
                "last_activity": status.last_activity,
                "session_timeout": status.session_timeout,
                "timestamp": time.time(),
                "pid": status.pid,
                "uptime": status.uptime
            }
            
            # Add additional data from calling service (e.g., model_loaded, device)
            if additional_data:
                status_data.update(additional_data)
            
            with open(self.status_file, 'w') as f:
                json.dump(status_data, f)
                
        except Exception as e:
            self.logger.warning(f"Status file update failed: {e}")
    
    def request_shutdown(self):
        """Request graceful session shutdown."""
        self.shutdown_requested = True
        self.logger.info("Session shutdown requested")
    
    def cleanup_session_files(self):
        """Clean up session persistence files."""
        files_to_cleanup = [self.pid_file, self.session_file, self.status_file]
        
        for file_path in files_to_cleanup:
            try:
                if file_path.exists():
                    file_path.unlink()
                    self.logger.debug(f"Cleaned up {file_path}")
            except Exception as e:
                self.logger.warning(f"Failed to cleanup {file_path}: {e}")
    
    def get_session_expiry_time(self) -> float:
        """Get timestamp when session will expire."""
        with self.activity_lock:
            return self.last_activity + self.session_timeout
    
    def get_time_until_expiry(self) -> float:
        """Get seconds until session expires."""
        return max(0, self.get_session_expiry_time() - time.time())
    
    def extend_session(self, additional_seconds: int = 0):
        """Extend session timeout (useful for debugging)."""
        if additional_seconds > 0:
            self.session_timeout += additional_seconds
            self.logger.info(f"Session extended by {additional_seconds}s (total: {self.session_timeout}s)")
        self.update_activity()
    
    def is_session_active(self) -> bool:
        """Check if session is still active."""
        return not self.shutdown_requested and not self.should_shutdown_due_to_timeout()


class SessionTimeoutMonitor:
    """
    Background monitor for session timeout handling.
    
    Runs in a separate thread to check for session expiry.
    """
    
    def __init__(self, coordinator: SessionCoordinator, check_interval: int = 30):
        self.coordinator = coordinator
        self.check_interval = check_interval
        self.monitor_thread = None
        self.logger = logging.getLogger(__name__)
    
    def start_monitoring(self):
        """Start background timeout monitoring."""
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.logger.warning("Session monitor already running")
            return
        
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info(f"Session timeout monitor started (check interval: {self.check_interval}s)")
    
    def _monitor_loop(self):
        """Background monitoring loop."""
        self.logger.info(f"Session monitor active (timeout: {self.coordinator.session_timeout}s)")
        
        while not self.coordinator.shutdown_requested:
            try:
                if self.coordinator.should_shutdown_due_to_timeout():
                    inactive_time = self.coordinator.get_inactive_time()
                    self.logger.info(f"Session inactive for {inactive_time:.1f}s, requesting shutdown...")
                    self.coordinator.request_shutdown()
                    break
                
                # Log session status periodically
                time_until_expiry = self.coordinator.get_time_until_expiry()
                if time_until_expiry < 60:  # Log when < 1 minute remaining
                    self.logger.info(f"Session expires in {time_until_expiry:.0f}s")
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"Session monitor error: {e}")
                time.sleep(60)  # Longer sleep on error
        
        self.logger.info("Session timeout monitor stopped")


# Utility functions for external session management
def check_existing_session() -> Optional[Dict[str, Any]]:
    """Check if a session daemon is already running."""
    pid_file = Path("/tmp/session_daemon.pid")
    status_file = Path("/tmp/session_daemon_status.json")
    
    if not pid_file.exists():
        return None
    
    try:
        with open(pid_file, 'r') as f:
            pid = int(f.read().strip())
        
        # Check if process is actually running
        os.kill(pid, 0)  # Signal 0 checks process existence
        
        # Check if status file is recent
        if status_file.exists():
            with open(status_file, 'r') as f:
                status = json.load(f)
            
            # Consider daemon responsive if status updated within last 60 seconds
            if time.time() - status.get('timestamp', 0) < 60:
                return {
                    "pid": pid,
                    "status": status,
                    "responsive": True
                }
        
        return {
            "pid": pid,
            "status": None,
            "responsive": False
        }
        
    except (ValueError, ProcessLookupError, FileNotFoundError):
        # Clean up stale PID file
        try:
            pid_file.unlink()
        except FileNotFoundError:
            pass
        return None


if __name__ == "__main__":
    # Test session coordinator
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    print("=== Session Coordinator Test ===")
    
    coordinator = SessionCoordinator(session_timeout=30)  # 30 second test
    monitor = SessionTimeoutMonitor(coordinator, check_interval=5)
    
    monitor.start_monitoring()
    
    # Simulate some activity
    for i in range(10):
        time.sleep(2)
        if i % 3 == 0:
            coordinator.update_activity()
            print(f"Activity updated - time until expiry: {coordinator.get_time_until_expiry():.1f}s")
        
        status = coordinator.get_session_status()
        coordinator.update_status_file({"test_iteration": i})
    
    print(f"Final session active: {coordinator.is_session_active()}")
    coordinator.cleanup_session_files()