"""
Add SYBOT to Windows startup
Run this script to automatically start SYBOT when Windows boots
"""

import os
import sys
import shutil
from pathlib import Path

def add_to_startup():
    """Add SYBOT.exe to Windows startup folder"""
    
    # Get paths
    script_dir = Path(__file__).parent
    exe_path = script_dir / "dist" / "SYBOT.exe"
    
    # Windows startup folder
    startup_folder = Path(os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"))
    
    # Destination path
    startup_exe = startup_folder / "SYBOT.exe"
    
    # Check if exe exists
    if not exe_path.exists():
        print(f"Error: SYBOT.exe not found at {exe_path}")
        print("Please build the executable first using: python -m PyInstaller sybot.spec")
        return False
    
    # Copy to startup folder
    try:
        shutil.copy2(exe_path, startup_exe)
        print(f"✓ SYBOT.exe copied to startup folder: {startup_exe}")
        print("✓ SYBOT will now start automatically when Windows boots")
        return True
    except Exception as e:
        print(f"Error copying to startup: {e}")
        return False

def remove_from_startup():
    """Remove SYBOT from Windows startup"""
    
    startup_folder = Path(os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"))
    startup_exe = startup_folder / "SYBOT.exe"
    
    if startup_exe.exists():
        try:
            startup_exe.unlink()
            print(f"✓ SYBOT.exe removed from startup folder")
            return True
        except Exception as e:
            print(f"Error removing from startup: {e}")
            return False
    else:
        print("SYBOT.exe not found in startup folder")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "remove":
        remove_from_startup()
    else:
        add_to_startup()
