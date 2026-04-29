"""
Automatic Tool Expansion System for SYBOT
Automatically installs or creates tools when needed
"""

import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional, List
from core.code_sandbox import CodeSandbox
from core.skill_system import SkillSystem


class ToolExpander:
    """Automatically expands SYBOT's capabilities by installing or creating tools"""
    
    def __init__(self, base_dir: Path, skill_system: SkillSystem, sandbox: CodeSandbox):
        self.base_dir = base_dir
        self.skill_system = skill_system
        self.sandbox = sandbox
        
        self.actions_dir = base_dir / "actions"
        self.actions_dir.mkdir(exist_ok=True)
        
        # Known package mappings
        self.package_map = {
            "screenshot": ["pillow", "mss"],
            "browser": ["selenium", "playwright"],
            "audio": ["sounddevice", "pyaudio"],
            "video": ["opencv-python"],
            "automation": ["pyautogui", "pyperclip"],
            "data": ["pandas", "numpy"],
            "web": ["requests", "beautifulsoup4"],
            "ai": ["openai", "google-generativeai"],
        }
    
    def check_capability(self, capability: str) -> bool:
        """Check if a capability exists"""
        # Check if action file exists
        action_file = self.actions_dir / f"{capability}.py"
        if action_file.exists():
            return True
        
        # Check if skill exists
        skills = self.skill_system.search_skills(capability)
        if skills:
            return True
        
        return False
    
    def expand_capability(self, capability: str, description: str = "") -> Dict:
        """Expand capabilities by installing or creating tools"""
        # First check if already exists
        if self.check_capability(capability):
            return {
                "success": True,
                "message": f"Capability '{capability}' already exists",
                "action": "none"
            }
        
        # Try to install required packages
        packages = self._get_packages_for_capability(capability)
        if packages:
            install_result = self._install_packages(packages)
            if not install_result["success"]:
                return install_result
        
        # Try to create a skill for the capability
        skill_result = self._create_skill_for_capability(capability, description)
        if skill_result["success"]:
            return skill_result
        
        return {
            "success": False,
            "message": f"Could not expand capability '{capability}'",
            "action": "failed"
        }
    
    def _get_packages_for_capability(self, capability: str) -> List[str]:
        """Get required packages for a capability"""
        capability_lower = capability.lower()
        
        for key, packages in self.package_map.items():
            if key in capability_lower:
                return packages
        
        return []
    
    def _install_packages(self, packages: List[str]) -> Dict:
        """Install required packages"""
        installed = []
        failed = []
        
        for package in packages:
            result = self.sandbox.install_package(package)
            if result["success"]:
                installed.append(package)
            else:
                failed.append(package)
        
        if failed:
            return {
                "success": False,
                "message": f"Failed to install packages: {', '.join(failed)}",
                "installed": installed,
                "failed": failed
            }
        
        return {
            "success": True,
            "message": f"Successfully installed: {', '.join(installed)}",
            "installed": installed
        }
    
    def _create_skill_for_capability(self, capability: str, description: str) -> Dict:
        """Create a skill for a capability using AI generation"""
        # This is a placeholder - in production, would use AI to generate code
        # For now, create a template skill
        
        template_code = f'''"""
Auto-generated skill for: {capability}
Description: {description}
"""

def execute_{capability}(**kwargs):
    """Execute {capability} capability"""
    # This is a template - implement the actual functionality
    result = {{
        "success": False,
        "message": "This is a template skill. Please implement the actual functionality.",
        "capability": "{capability}"
    }}
    return result

if __name__ == "__main__":
    # Test the skill
    result = execute_{capability}()
    print(result)
'''
        
        try:
            skill_id = self.skill_system.add_skill(
                name=capability,
                category="auto_generated",
                code=template_code,
                description=description or f"Auto-generated skill for {capability}"
            )
            
            return {
                "success": True,
                "message": f"Created template skill for '{capability}'",
                "skill_id": skill_id,
                "action": "skill_created"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to create skill: {str(e)}",
                "action": "skill_creation_failed"
            }
    
    def list_missing_capabilities(self, required_capabilities: List[str]) -> List[str]:
        """List capabilities that are missing"""
        missing = []
        for cap in required_capabilities:
            if not self.check_capability(cap):
                missing.append(cap)
        return missing
    
    def auto_expand(self, required_capabilities: List[str]) -> Dict:
        """Automatically expand for all missing capabilities"""
        missing = self.list_missing_capabilities(required_capabilities)
        
        if not missing:
            return {
                "success": True,
                "message": "All required capabilities exist",
                "expanded": []
            }
        
        results = []
        for cap in missing:
            result = self.expand_capability(cap)
            results.append({
                "capability": cap,
                "result": result
            })
        
        successful = [r for r in results if r["result"]["success"]]
        
        return {
            "success": len(successful) == len(missing),
            "message": f"Expanded {len(successful)}/{len(missing)} capabilities",
            "expanded": successful,
            "failed": [r for r in results if not r["result"]["success"]]
        }
