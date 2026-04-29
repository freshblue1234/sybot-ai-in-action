"""
Create desktop shortcut for SYBOT
"""

import os
import sys
from pathlib import Path
import winshell
from win32com.client import Dispatch

def create_desktop_shortcut():
    """Create a desktop shortcut for SYBOT.exe"""
    
    # Get paths
    script_dir = Path(__file__).parent
    exe_path = script_dir / "dist" / "SYBOT.exe"
    
    # Desktop path
    desktop = Path(os.path.expandvars(r"%USERPROFILE%\Desktop"))
    shortcut_path = desktop / "SYBOT.lnk"
    
    # Check if exe exists
    if not exe_path.exists():
        print(f"Error: SYBOT.exe not found at {exe_path}")
        print("Please build the executable first using: python -m PyInstaller sybot.spec")
        return False
    
    # Create shortcut
    try:
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(str(shortcut_path))
        shortcut.Targetpath = str(exe_path)
        shortcut.WorkingDirectory = str(script_dir)
        shortcut.Description = "SYBOT AI Assistant"
        shortcut.save()
        
        print(f"✓ Desktop shortcut created: {shortcut_path}")
        print("✓ Double-click the shortcut to launch SYBOT")
        return True
    except Exception as e:
        print(f"Error creating shortcut: {e}")
        return False

if __name__ == "__main__":
    create_desktop_shortcut()
