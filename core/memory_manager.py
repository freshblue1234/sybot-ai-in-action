"""
Memory Management System for SYBOT
Persistent additive memory that never overwrites, only merges
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from copy import deepcopy


class MemoryManager:
    """Manages persistent additive memory for users"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.memory_file = base_dir / "memory" / "long_term.json"
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.memory: Dict[str, Any] = self._load_memory()
    
    def _load_memory(self) -> Dict[str, Any]:
        """Load memory from file, never overwrite"""
        if not self.memory_file.exists():
            return {
                "version": "2.0",
                "created": datetime.now().isoformat(),
                "users": {},
                "global_context": {}
            }
        
        try:
            with open(self.memory_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Memory] Failed to load memory: {e}")
            return {
                "version": "2.0",
                "created": datetime.now().isoformat(),
                "users": {},
                "global_context": {}
            }
    
    def _save_memory(self):
        """Save memory to file"""
        self.memory["last_updated"] = datetime.now().isoformat()
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump(self.memory, f, indent=2, ensure_ascii=False)
    
    def add_user_memory(self, user_id: str, category: str, key: str, value: Any):
        """Add or merge memory for a user (never overwrite)"""
        if "users" not in self.memory:
            self.memory["users"] = {}
        
        if user_id not in self.memory["users"]:
            self.memory["users"][user_id] = {
                "created": datetime.now().isoformat(),
                "profile": {},
                "preferences": {},
                "projects": {},
                "relationships": {},
                "wishes": {},
                "notes": {},
                "interaction_history": []
            }
        
        user_memory = self.memory["users"][user_id]
        
        # Add to category
        if category not in user_memory:
            user_memory[category] = {}
        
        existing = user_memory[category].get(key)
        
        # Merge strategy: if it's a dict, merge; if it's a list, append; otherwise update
        if isinstance(existing, dict) and isinstance(value, dict):
            # Merge dictionaries
            merged = deepcopy(existing)
            merged.update(value)
            user_memory[category][key] = {
                "value": merged,
                "updated": datetime.now().isoformat()
            }
        elif isinstance(existing, list) and isinstance(value, list):
            # Append to list (avoid duplicates)
            merged = deepcopy(existing)
            for item in value:
                if item not in merged:
                    merged.append(item)
            user_memory[category][key] = {
                "value": merged,
                "updated": datetime.now().isoformat()
            }
        else:
            # Simple update with timestamp
            user_memory[category][key] = {
                "value": value,
                "updated": datetime.now().isoformat()
            }
        
        self._save_memory()
    
    def get_user_memory(self, user_id: str, category: str = None, key: str = None) -> Any:
        """Get memory for a user"""
        if "users" not in self.memory or user_id not in self.memory["users"]:
            return None
        
        user_memory = self.memory["users"][user_id]
        
        if category:
            if category not in user_memory:
                return None
            if key:
                item = user_memory[category].get(key)
                return item["value"] if item else None
            return user_memory[category]
        
        return user_memory
    
    def add_interaction(self, user_id: str, interaction: Dict):
        """Add interaction to history"""
        if "users" not in self.memory or user_id not in self.memory["users"]:
            return
        
        interaction["timestamp"] = datetime.now().isoformat()
        self.memory["users"][user_id]["interaction_history"].append(interaction)
        
        # Keep only last 100 interactions
        history = self.memory["users"][user_id]["interaction_history"]
        if len(history) > 100:
            self.memory["users"][user_id]["interaction_history"] = history[-100:]
        
        self._save_memory()
    
    def get_interaction_history(self, user_id: str, limit: int = 10) -> list:
        """Get recent interactions for a user"""
        user_memory = self.get_user_memory(user_id)
        if not user_memory:
            return []
        
        history = user_memory.get("interaction_history", [])
        return history[-limit:] if history else []
    
    def add_global_context(self, key: str, value: Any):
        """Add global context (shared across all users)"""
        if "global_context" not in self.memory:
            self.memory["global_context"] = {}
        
        self.memory["global_context"][key] = {
            "value": value,
            "updated": datetime.now().isoformat()
        }
        
        self._save_memory()
    
    def get_global_context(self, key: str = None) -> Any:
        """Get global context"""
        if "global_context" not in self.memory:
            return None
        
        if key:
            item = self.memory["global_context"].get(key)
            return item["value"] if item else None
        
        return self.memory["global_context"]
    
    def get_user_summary(self, user_id: str) -> str:
        """Get a summary of user memory for AI context"""
        user_memory = self.get_user_memory(user_id)
        if not user_memory:
            return "No memory available for this user."
        
        summary_parts = []
        
        # Profile
        profile = user_memory.get("profile", {})
        if profile:
            summary_parts.append("Profile:")
            for key, item in profile.items():
                summary_parts.append(f"  {key}: {item.get('value', item)}")
        
        # Preferences
        prefs = user_memory.get("preferences", {})
        if prefs:
            summary_parts.append("Preferences:")
            for key, item in prefs.items():
                summary_parts.append(f"  {key}: {item.get('value', item)}")
        
        # Projects
        projects = user_memory.get("projects", {})
        if projects:
            summary_parts.append("Projects:")
            for key, item in projects.items():
                summary_parts.append(f"  {key}: {item.get('value', item)}")
        
        # Recent interactions
        history = self.get_interaction_history(user_id, limit=5)
        if history:
            summary_parts.append("Recent interactions:")
            for interaction in history[-3:]:
                summary_parts.append(f"  - {interaction.get('intent', 'unknown')}: {interaction.get('summary', 'no summary')}")
        
        return "\n".join(summary_parts) if summary_parts else "No detailed memory available."
