"""
User Profile Management System for SYBOT
Handles multi-user profiles, voice embeddings, and leader prioritization
"""
import json
import pickle
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict


@dataclass
class UserProfile:
    """User profile with voice embedding and preferences"""
    user_id: str
    name: str
    voice_embedding: Optional[bytes] = None
    is_leader: bool = False
    preferences: Dict = None
    interaction_count: int = 0
    last_seen: str = None
    emotional_baseline: str = "neutral"
    
    def __post_init__(self):
        if self.preferences is None:
            self.preferences = {}
        if self.last_seen is None:
            self.last_seen = datetime.now().isoformat()


class UserManager:
    """Manages user profiles, voice recognition, and leader prioritization"""
    
    LEADER_NAME = "Nshuti Moise"
    LEADER_ID = "leader_001"
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.profiles_dir = base_dir / "memory" / "user_profiles"
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_user: Optional[UserProfile] = None
        self.profiles: Dict[str, UserProfile] = {}
        
        self._load_profiles()
        self._ensure_leader_exists()
    
    def _load_profiles(self):
        """Load all user profiles from disk"""
        for profile_file in self.profiles_dir.glob("*.pkl"):
            try:
                with open(profile_file, "rb") as f:
                    profile = pickle.load(f)
                    self.profiles[profile.user_id] = profile
            except Exception as e:
                print(f"[UserManager] Failed to load {profile_file}: {e}")
    
    def _ensure_leader_exists(self):
        """Ensure Nshuti Moise profile exists as leader"""
        if self.LEADER_ID not in self.profiles:
            leader_profile = UserProfile(
                user_id=self.LEADER_ID,
                name=self.LEADER_NAME,
                is_leader=True,
                emotional_baseline="neutral"
            )
            self.profiles[self.LEADER_ID] = leader_profile
            self._save_profile(leader_profile)
            print(f"[UserManager] Created leader profile: {self.LEADER_NAME}")
    
    def _save_profile(self, profile: UserProfile):
        """Save profile to disk"""
        profile_file = self.profiles_dir / f"{profile.user_id}.pkl"
        with open(profile_file, "wb") as f:
            pickle.dump(profile, f)
    
    def get_or_create_user(self, user_id: str, name: str = None) -> UserProfile:
        """Get existing user or create new profile"""
        if user_id in self.profiles:
            profile = self.profiles[user_id]
            profile.last_seen = datetime.now().isoformat()
            profile.interaction_count += 1
            self._save_profile(profile)
            return profile
        
        # Create new user
        profile = UserProfile(
            user_id=user_id,
            name=name or f"User_{len(self.profiles) + 1}",
            is_leader=(name == self.LEADER_NAME),
            emotional_baseline="neutral"
        )
        self.profiles[user_id] = profile
        self._save_profile(profile)
        
        print(f"[UserManager] Created new profile: {profile.name} (ID: {user_id})")
        return profile
    
    def set_current_user(self, user_id: str, name: str = None):
        """Set the currently active user"""
        self.current_user = self.get_or_create_user(user_id, name)
        print(f"[UserManager] Current user: {self.current_user.name} (Leader: {self.current_user.is_leader})")
    
    def get_current_user(self) -> Optional[UserProfile]:
        """Get current user profile"""
        return self.current_user
    
    def update_profile(self, user_id: str, **kwargs):
        """Update user profile"""
        if user_id not in self.profiles:
            return
        
        profile = self.profiles[user_id]
        for key, value in kwargs.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        
        profile.last_seen = datetime.now().isoformat()
        self._save_profile(profile)
    
    def is_guest(self) -> bool:
        """Check if current user is a guest"""
        current = self.get_current_user()
        return current and current.user_id.startswith("guest_")
    
    def is_leader(self, user_id: str = None) -> bool:
        """Check if user is the leader (Nshuti Moise)"""
        if user_id:
            return self.profiles.get(user_id, UserProfile(user_id="", name="")).is_leader
        return self.current_user.is_leader if self.current_user else False
    
    def update_user_preference(self, key: str, value: any):
        """Update user preference"""
        if self.current_user:
            self.current_user.preferences[key] = value
            self._save_profile(self.current_user)
    
    def get_user_preference(self, key: str, default=None):
        """Get user preference"""
        if self.current_user:
            return self.current_user.preferences.get(key, default)
        return default
    
    def list_users(self) -> List[Dict]:
        """List all users (for admin purposes)"""
        return [
            {
                "user_id": p.user_id,
                "name": p.name,
                "is_leader": p.is_leader,
                "interaction_count": p.interaction_count,
                "last_seen": p.last_seen
            }
            for p in self.profiles.values()
        ]
    
    def identify_user_by_voice(self, user_id: str) -> Optional[UserProfile]:
        """Identify user by voice ID and switch to them automatically"""
        if user_id not in self.profiles:
            return None
        
        # Switch to this user
        self.current_user = self.profiles[user_id]
        profile = self.current_user
        profile.last_seen = datetime.now().isoformat()
        profile.interaction_count += 1
        self._save_profile(profile)
        
        print(f"[UserManager] Auto-switched to: {profile.name} (Leader: {profile.is_leader})")
        return profile
    
    def create_guest_user(self) -> UserProfile:
        """Create a guest user profile for unknown speakers"""
        guest_id = f"guest_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        profile = UserProfile(
            user_id=guest_id,
            name="Guest",
            is_leader=False,
            preferences={},
            interaction_count=0,
            last_seen=datetime.now().isoformat(),
            emotional_baseline="neutral"
        )
        self.profiles[guest_id] = profile
        self._save_profile(profile)
        print(f"[UserManager] Created guest user: {guest_id}")
        self.current_user = profile
        return profile
    
    def auto_enroll_user(self, user_id: str, user_name: str, voice_embedding: bytes = None) -> UserProfile:
        """Automatically enroll a new user from voice identification"""
        if user_id in self.profiles:
            return self.profiles[user_id]
        
        profile = UserProfile(
            user_id=user_id,
            name=user_name,
            voice_embedding=voice_embedding,
            is_leader=(user_id == self.LEADER_ID),
            preferences={},
            interaction_count=0,
            last_seen=datetime.now().isoformat(),
            emotional_baseline="neutral"
        )
        self.profiles[user_id] = profile
        self._save_profile(profile)
        print(f"[UserManager] Auto-enrolled: {user_name} ({user_id})")
        return profile
