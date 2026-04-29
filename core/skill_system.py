"""
Skill System for SYBOT
Modular skill storage and management for reusable capabilities
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime


class Skill:
    """Represents a reusable skill/capability"""
    
    def __init__(self, skill_id: str, name: str, category: str, code: str, description: str):
        self.skill_id = skill_id
        self.name = name
        self.category = category
        self.code = code
        self.description = description
        self.created_at = datetime.now().isoformat()
        self.usage_count = 0
        self.success_rate = 1.0  # Start with 100% success rate
    
    def to_dict(self) -> Dict:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "category": self.category,
            "code": self.code,
            "description": self.description,
            "created_at": self.created_at,
            "usage_count": self.usage_count,
            "success_rate": self.success_rate
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Skill':
        skill = cls(
            data["skill_id"],
            data["name"],
            data["category"],
            data["code"],
            data["description"]
        )
        skill.created_at = data.get("created_at", datetime.now().isoformat())
        skill.usage_count = data.get("usage_count", 0)
        skill.success_rate = data.get("success_rate", 1.0)
        return skill


class SkillSystem:
    """Manages modular skills for SYBOT"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.skills_dir = base_dir / "skills"
        self.skills_dir.mkdir(exist_ok=True)
        
        self.skills_index_file = self.skills_dir / "skills_index.json"
        self.skills: Dict[str, Skill] = {}
        
        self._load_skills()
    
    def _load_skills(self):
        """Load skills from storage"""
        if self.skills_index_file.exists():
            try:
                with open(self.skills_index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for skill_data in data.get("skills", []):
                        skill = Skill.from_dict(skill_data)
                        self.skills[skill.skill_id] = skill
            except Exception as e:
                print(f"[SkillSystem] Error loading skills: {e}")
    
    def _save_skills(self):
        """Save skills to storage"""
        try:
            data = {
                "skills": [skill.to_dict() for skill in self.skills.values()],
                "last_updated": datetime.now().isoformat()
            }
            with open(self.skills_index_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[SkillSystem] Error saving skills: {e}")
    
    def _generate_skill_id(self, name: str) -> str:
        """Generate unique skill ID"""
        hash_input = f"{name}_{datetime.now().isoformat()}".encode()
        return f"skill_{hashlib.md5(hash_input).hexdigest()[:12]}"
    
    def add_skill(self, name: str, category: str, code: str, description: str) -> str:
        """Add a new skill"""
        skill_id = self._generate_skill_id(name)
        skill = Skill(skill_id, name, category, code, description)
        self.skills[skill_id] = skill
        
        # Save skill code to file
        skill_file = self.skills_dir / f"{skill_id}.py"
        with open(skill_file, 'w', encoding='utf-8') as f:
            f.write(code)
        
        self._save_skills()
        return skill_id
    
    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """Get a skill by ID"""
        return self.skills.get(skill_id)
    
    def get_skills_by_category(self, category: str) -> List[Skill]:
        """Get all skills in a category"""
        return [skill for skill in self.skills.values() if skill.category == category]
    
    def search_skills(self, query: str) -> List[Skill]:
        """Search skills by name or description"""
        query_lower = query.lower()
        return [
            skill for skill in self.skills.values()
            if query_lower in skill.name.lower() or query_lower in skill.description.lower()
        ]
    
    def record_usage(self, skill_id: str, success: bool):
        """Record skill usage and update success rate"""
        skill = self.skills.get(skill_id)
        if skill:
            skill.usage_count += 1
            # Update success rate with moving average
            current_rate = skill.success_rate
            new_rate = (current_rate * (skill.usage_count - 1) + (1 if success else 0)) / skill.usage_count
            skill.success_rate = new_rate
            self._save_skills()
    
    def get_skill_code(self, skill_id: str) -> Optional[str]:
        """Get the code for a skill"""
        skill_file = self.skills_dir / f"{skill_id}.py"
        if skill_file.exists():
            return skill_file.read_text(encoding='utf-8')
        return None
    
    def delete_skill(self, skill_id: str) -> bool:
        """Delete a skill"""
        if skill_id in self.skills:
            del self.skills[skill_id]
            skill_file = self.skills_dir / f"{skill_id}.py"
            if skill_file.exists():
                skill_file.unlink()
            self._save_skills()
            return True
        return False
    
    def get_all_skills(self) -> List[Skill]:
        """Get all skills"""
        return list(self.skills.values())
    
    def get_skill_stats(self) -> Dict:
        """Get statistics about skills"""
        total_skills = len(self.skills)
        total_usage = sum(skill.usage_count for skill in self.skills.values())
        avg_success_rate = sum(skill.success_rate for skill in self.skills.values()) / total_skills if total_skills > 0 else 0
        
        categories = {}
        for skill in self.skills.values():
            if skill.category not in categories:
                categories[skill.category] = 0
            categories[skill.category] += 1
        
        return {
            "total_skills": total_skills,
            "total_usage": total_usage,
            "average_success_rate": avg_success_rate,
            "categories": categories
        }
