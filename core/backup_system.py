"""
Backup System for SYBOT - Lightweight fallback mode
Provides basic functionality when primary system fails
"""

import asyncio
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime


class BackupSystem:
    """Lightweight backup system for SYBOT"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.backup_config = base_dir / "memory" / "backup_config.json"
        self.active = False
        self._basic_commands = {
            "help": self._cmd_help,
            "status": self._cmd_status,
            "restart": self._cmd_restart,
            "exit": self._cmd_exit,
        }
        
    def activate(self):
        """Activate backup system"""
        self.active = True
        print("[BackupSystem] ⚠️ Activated - Running in lightweight mode")
        print("[BackupSystem] Basic commands available: help, status, restart, exit")
    
    def deactivate(self):
        """Deactivate backup system"""
        self.active = False
        print("[BackupSystem] ✅ Deactivated - Returning to primary system")
    
    def is_active(self) -> bool:
        """Check if backup system is active"""
        return self.active
    
    def process_command(self, command: str) -> str:
        """Process a command in backup mode"""
        if not self.active:
            return "Backup system not active"
        
        cmd = command.strip().lower()
        
        # Check basic commands
        for key, handler in self._basic_commands.items():
            if cmd.startswith(key):
                return handler(command)
        
        # For other commands, acknowledge but indicate limited functionality
        return f"[Backup Mode] Command '{command}' acknowledged. Full functionality requires primary system. Type 'restart' to attempt recovery."
    
    def _cmd_help(self, command: str) -> str:
        """Show help in backup mode"""
        return """
[Backup Mode - Help]
Available commands:
- help: Show this help
- status: Show system status
- restart: Attempt to restart primary system
- exit: Exit SYBOT

Note: Backup mode provides limited functionality. 
Restart the primary system for full features.
"""
    
    def _cmd_status(self, command: str) -> str:
        """Show system status"""
        return f"""
[Backup Mode - Status]
Mode: Lightweight Backup
Active: {self.active}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Primary System: Offline
"""
    
    def _cmd_restart(self, command: str) -> str:
        """Signal intent to restart primary system"""
        return "[Backup Mode] Restart requested. Deactivating backup mode to allow primary system recovery."
    
    def _cmd_exit(self, command: str) -> str:
        """Exit SYBOT"""
        return "[Backup Mode] Exit requested. Shutting down SYBOT."
    
    def get_basic_response(self, user_input: str) -> str:
        """Generate a basic response for user input in backup mode"""
        if not self.active:
            return None
        
        # Simple keyword-based responses
        input_lower = user_input.lower()
        
        if any(word in input_lower for word in ["hello", "hi", "hey"]):
            return "Hello. SYBOT is currently in backup mode. Type 'help' for available commands."
        
        if any(word in input_lower for word in ["what can you do", "help", "commands"]):
            return self._cmd_help("")
        
        if any(word in input_lower for word in ["status", "how are you"]):
            return self._cmd_status("")
        
        # Default response
        return "SYBOT is in backup mode with limited functionality. Type 'help' for available commands or 'restart' to attempt recovery."
    
    def save_backup_state(self, state: Dict[str, Any]):
        """Save state during backup mode"""
        try:
            self.backup_config.parent.mkdir(parents=True, exist_ok=True)
            with open(self.backup_config, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'state': state
                }, f, indent=2)
        except Exception as e:
            print(f"[BackupSystem] Failed to save state: {e}")
    
    def load_backup_state(self) -> Optional[Dict[str, Any]]:
        """Load state from backup mode"""
        try:
            if self.backup_config.exists():
                with open(self.backup_config, 'r') as f:
                    data = json.load(f)
                    return data.get('state')
        except Exception as e:
            print(f"[BackupSystem] Failed to load state: {e}")
        return None
