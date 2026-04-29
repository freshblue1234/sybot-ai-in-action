"""
Health Monitoring and Self-Healing System for SYBOT
Monitors system health and provides automatic failover capabilities
"""

import threading
import time
import traceback
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Callable
import json


@dataclass
class HealthStatus:
    """Current health status of the system"""
    is_healthy: bool = True
    primary_active: bool = True
    last_check: str = ""
    error_count: int = 0
    last_error: str = ""
    failover_count: int = 0


class HealthMonitor:
    """Monitors SYBOT health and manages failover"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.health_file = base_dir / "memory" / "health_status.json"
        self.status = HealthStatus()
        self._lock = threading.Lock()
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._on_failover: Optional[Callable] = None
        self._on_recovery: Optional[Callable] = None
        
        # Health thresholds
        self.MAX_ERRORS = 5
        self.CHECK_INTERVAL = 30  # seconds
        
        # Load previous status
        self._load_status()
    
    def _load_status(self):
        """Load health status from disk"""
        try:
            if self.health_file.exists():
                with open(self.health_file, 'r') as f:
                    data = json.load(f)
                    self.status.failover_count = data.get('failover_count', 0)
        except Exception:
            pass
    
    def _save_status(self):
        """Save health status to disk"""
        try:
            self.health_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.health_file, 'w') as f:
                json.dump({
                    'is_healthy': self.status.is_healthy,
                    'primary_active': self.status.primary_active,
                    'last_check': self.status.last_check,
                    'error_count': self.status.error_count,
                    'last_error': self.status.last_error,
                    'failover_count': self.status.failover_count
                }, f, indent=2)
        except Exception:
            pass
    
    def register_failover_callback(self, callback: Callable):
        """Register callback for failover events"""
        self._on_failover = callback
    
    def register_recovery_callback(self, callback: Callable):
        """Register callback for recovery events"""
        self._on_recovery = callback
    
    def report_error(self, error: str):
        """Report an error to the health monitor"""
        with self._lock:
            self.status.error_count += 1
            self.status.last_error = error
            self.status.last_check = datetime.now().isoformat()
            
            # Check if we need failover
            if self.status.error_count >= self.MAX_ERRORS and self.status.primary_active:
                self._trigger_failover()
            
            self._save_status()
    
    def report_success(self):
        """Report a successful operation"""
        with self._lock:
            self.status.error_count = max(0, self.status.error_count - 1)
            self.status.last_check = datetime.now().isoformat()
            
            # If we were in backup mode, check if we can recover
            if not self.status.primary_active and self.status.error_count == 0:
                self._trigger_recovery()
            
            self._save_status()
    
    def _trigger_failover(self):
        """Trigger failover to backup system"""
        self.status.primary_active = False
        self.status.failover_count += 1
        self.status.is_healthy = True  # Backup is healthy
        
        print(f"[HealthMonitor] ⚠️ Failover triggered (count: {self.status.failover_count})")
        
        if self._on_failover:
            try:
                self._on_failover()
            except Exception as e:
                print(f"[HealthMonitor] Failover callback error: {e}")
    
    def _trigger_recovery(self):
        """Trigger recovery to primary system"""
        self.status.primary_active = True
        self.status.is_healthy = True
        
        print(f"[HealthMonitor] ✅ Recovery triggered - back to primary")
        
        if self._on_recovery:
            try:
                self._on_recovery()
            except Exception as e:
                print(f"[HealthMonitor] Recovery callback error: {e}")
    
    def get_status(self) -> HealthStatus:
        """Get current health status"""
        with self._lock:
            return HealthStatus(
                is_healthy=self.status.is_healthy,
                primary_active=self.status.primary_active,
                last_check=self.status.last_check,
                error_count=self.status.error_count,
                last_error=self.status.last_error,
                failover_count=self.status.failover_count
            )
    
    def start_monitoring(self):
        """Start health monitoring thread"""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        print("[HealthMonitor] Monitoring started")
    
    def stop_monitoring(self):
        """Stop health monitoring thread"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        print("[HealthMonitor] Monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self._monitoring:
            try:
                time.sleep(self.CHECK_INTERVAL)
                
                # Periodic health check
                with self._lock:
                    self.status.last_check = datetime.now().isoformat()
                    self._save_status()
                    
            except Exception as e:
                print(f"[HealthMonitor] Monitor loop error: {e}")
    
    def force_failover(self):
        """Manually trigger failover (for testing)"""
        with self._lock:
            self._trigger_failover()
            self._save_status()
    
    def force_recovery(self):
        """Manually trigger recovery (for testing)"""
        with self._lock:
            self._trigger_recovery()
            self._save_status()
