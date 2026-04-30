"""
Event Monitor for SYBOT
Monitors system events, user activity, and triggers appropriate responses.
"""

import asyncio
import threading
import time
import os
import psutil
from pathlib import Path
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from core.orchestrator import EventType, Event


@dataclass
class MonitoredPath:
    """A path being monitored for changes"""
    path: Path
    recursive: bool = True
    last_modified: Optional[datetime] = None


class FileChangeHandler(FileSystemEventHandler):
    """Handler for file system events"""
    
    def __init__(self, callback: Callable):
        self.callback = callback
    
    def on_modified(self, event):
        if not event.is_directory:
            self.callback(EventType.FILE_CHANGE, {
                "path": event.src_path,
                "event_type": "modified",
                "timestamp": datetime.now().isoformat()
            })
    
    def on_created(self, event):
        if not event.is_directory:
            self.callback(EventType.FILE_CHANGE, {
                "path": event.src_path,
                "event_type": "created",
                "timestamp": datetime.now().isoformat()
            })
    
    def on_deleted(self, event):
        if not event.is_directory:
            self.callback(EventType.FILE_CHANGE, {
                "path": event.src_path,
                "event_type": "deleted",
                "timestamp": datetime.now().isoformat()
            })


class EventMonitor:
    """
    Monitors system events and emits them to the orchestrator.
    """
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.running = False
        self.monitor_thread: Optional[threading.Thread] = None
        
        # File monitoring
        self.monitored_paths: List[MonitoredPath] = []
        self.observer: Optional[Observer] = None
        
        # Application monitoring
        self.previous_processes: Dict[int, str] = {}
        self.check_interval = 5  # seconds
        
        # Timer events
        self.timers: Dict[str, datetime] = {}
        
        # User presence
        self.last_activity: Optional[datetime] = None
        self.idle_threshold = 300  # 5 minutes
        self.presence_check_interval = 30  # seconds
    
    def start(self):
        """Start the event monitor"""
        if self.running:
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        # Start file observer
        self.observer = Observer()
        self.observer.start()
        
        # Emit startup event
        self.orchestrator.emit_event(EventType.SYSTEM_CHANGE, {
            "event": "monitor_started",
            "timestamp": datetime.now().isoformat()
        })
    
    def stop(self):
        """Stop the event monitor"""
        self.running = False
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        
        if self.observer:
            self.observer.stop()
            self.observer.join()
    
    def add_monitored_path(self, path: str, recursive: bool = True):
        """Add a path to monitor for file changes"""
        monitored = MonitoredPath(Path(path), recursive)
        self.monitored_paths.append(monitored)
        
        # Add to observer
        handler = FileChangeHandler(self.orchestrator.emit_event)
        self.observer.schedule(handler, path, recursive=recursive)
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                self._check_applications()
                self._check_user_presence()
                self._check_timers()
                time.sleep(self.check_interval)
            except Exception as e:
                print(f"[EventMonitor] Error in monitor loop: {e}")
                time.sleep(self.check_interval)
    
    def _check_applications(self):
        """Check for application launches/closes"""
        try:
            current_processes = {}
            
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    current_processes[proc.info['pid']] = proc.info['name']
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Check for new applications
            for pid, name in current_processes.items():
                if pid not in self.previous_processes:
                    try:
                        self.orchestrator.emit_event(EventType.APPLICATION_LAUNCH, {
                            "pid": pid,
                            "name": name,
                            "event": "launched",
                            "timestamp": datetime.now().isoformat()
                        })
                    except Exception as e:
                        print(f"[EventMonitor] Error emitting launch event: {e}")
            
            # Check for closed applications
            for pid, name in self.previous_processes.items():
                if pid not in current_processes:
                    try:
                        self.orchestrator.emit_event(EventType.APPLICATION_LAUNCH, {
                            "pid": pid,
                            "name": name,
                            "event": "closed",
                            "timestamp": datetime.now().isoformat()
                        })
                    except Exception as e:
                        print(f"[EventMonitor] Error emitting close event: {e}")
            
            self.previous_processes = current_processes
        except Exception as e:
            print(f"[EventMonitor] Error checking applications: {e}")
    
    def _check_user_presence(self):
        """Check if user is active or idle"""
        try:
            # Get last input time (Windows only)
            try:
                import ctypes
                class LASTINPUTINFO(ctypes.Structure):
                    _fields_ = [
                        ('cbSize', ctypes.c_uint),
                        ('dwTime', ctypes.c_uint)
                    ]
                
                lastInputInfo = LASTINPUTINFO()
                lastInputInfo.cbSize = ctypes.sizeof(lastInputInfo)
                ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lastInputInfo))
                
                idle_time = (time.time() - (lastInputInfo.dwTime / 1000.0))
                
                if idle_time < self.idle_threshold:
                    if self.last_activity is None or \
                       (datetime.now() - self.last_activity) > timedelta(seconds=self.presence_check_interval):
                        self.last_activity = datetime.now()
                        try:
                            self.orchestrator.emit_event(EventType.USER_PRESENCE, {
                                "status": "active",
                                "idle_time": idle_time,
                                "timestamp": datetime.now().isoformat()
                            })
                        except Exception as e:
                            print(f"[EventMonitor] Error emitting presence event: {e}")
                else:
                    if self.last_activity is not None:
                        try:
                            self.orchestrator.emit_event(EventType.USER_PRESENCE, {
                                "status": "idle",
                                "idle_time": idle_time,
                                "timestamp": datetime.now().isoformat()
                            })
                        except Exception as e:
                            print(f"[EventMonitor] Error emitting idle event: {e}")
                        self.last_activity = None
            except Exception as e:
                # Fallback: just skip presence check if ctypes fails
                pass
        except Exception as e:
            print(f"[EventMonitor] Error checking user presence: {e}")
    
    def _check_timers(self):
        """Check for timer events"""
        try:
            now = datetime.now()
            expired_timers = []
            
            for timer_id, trigger_time in self.timers.items():
                if now >= trigger_time:
                    try:
                        self.orchestrator.emit_event(EventType.TIMER, {
                            "timer_id": timer_id,
                            "trigger_time": trigger_time.isoformat(),
                            "timestamp": now.isoformat()
                        })
                    except Exception as e:
                        print(f"[EventMonitor] Error emitting timer event: {e}")
                    expired_timers.append(timer_id)
            
            for timer_id in expired_timers:
                if timer_id in self.timers:
                    del self.timers[timer_id]
        except Exception as e:
            print(f"[EventMonitor] Error checking timers: {e}")
    
    def set_timer(self, timer_id: str, delay_seconds: int):
        """Set a timer to trigger after delay_seconds"""
        trigger_time = datetime.now() + timedelta(seconds=delay_seconds)
        self.timers[timer_id] = trigger_time
    
    def cancel_timer(self, timer_id: str):
        """Cancel a timer"""
        if timer_id in self.timers:
            del self.timers[timer_id]
    
    def emit_voice_command(self, command: str, confidence: float):
        """Emit a voice command event"""
        self.orchestrator.emit_event(EventType.VOICE_COMMAND, {
            "command": command,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat()
        })
    
    def emit_manual_trigger(self, trigger_type: str, data: Dict = None):
        """Emit a manually triggered event"""
        self.orchestrator.emit_event(EventType.MANUAL_TRIGGER, {
            "trigger_type": trigger_type,
            "data": data or {},
            "timestamp": datetime.now().isoformat()
        })
