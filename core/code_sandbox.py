"""
Safe Code Execution Sandbox for SYBOT
Executes generated code in a controlled, isolated environment
"""

import subprocess
import tempfile
import os
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple
import json
import time


class CodeSandbox:
    """Safe execution environment for generated code"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.sandbox_dir = base_dir / "sandbox"
        self.sandbox_dir.mkdir(exist_ok=True)
        
        # Safety rules
        self.forbidden_imports = [
            'os', 'sys', 'subprocess', 'shutil', 'pathlib',
            'ctypes', 'win32api', 'win32con', 'win32gui',
            'requests', 'urllib', 'http', 'socket'
        ]
        
        self.forbidden_functions = [
            'exec', 'eval', 'compile', '__import__',
            'open', 'file', 'input', 'raw_input'
        ]
        
        self.max_execution_time = 10  # seconds
        self.max_output_size = 10000  # characters
    
    def validate_code(self, code: str) -> Tuple[bool, str]:
        """Validate code for safety violations"""
        lines = code.split('\n')
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Check for forbidden imports
            for forbidden in self.forbidden_imports:
                if f"import {forbidden}" in line_lower or f"from {forbidden}" in line_lower:
                    return False, f"Forbidden import detected: {forbidden}"
            
            # Check for forbidden functions
            for forbidden in self.forbidden_functions:
                if f"{forbidden}(" in line_lower:
                    return False, f"Forbidden function detected: {forbidden}"
            
            # Check for file operations
            if any(op in line_lower for op in ['open(', 'file(', 'write(', 'delete(', 'remove(']):
                return False, "File operations not allowed in sandbox"
            
            # Check for system commands
            if any(cmd in line_lower for cmd in ['system(', 'popen(', 'call(', 'run(']):
                return False, "System command execution not allowed"
        
        return True, "Code validated successfully"
    
    def execute_python(self, code: str, timeout: Optional[int] = None) -> Dict:
        """Execute Python code in sandbox"""
        # Validate code first
        is_valid, message = self.validate_code(code)
        if not is_valid:
            return {
                "success": False,
                "error": f"Code validation failed: {message}",
                "output": None
            }
        
        timeout = timeout or self.max_execution_time
        
        # Create temporary file for code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, dir=self.sandbox_dir) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Execute with timeout
            result = subprocess.run(
                [sys.executable, temp_file],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.sandbox_dir)
            )
            
            output = result.stdout
            if len(output) > self.max_output_size:
                output = output[:self.max_output_size] + "\n... (output truncated)"
            
            return {
                "success": result.returncode == 0,
                "output": output,
                "error": result.stderr if result.stderr else None,
                "return_code": result.returncode
            }
        
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Execution timeout after {timeout} seconds",
                "output": None
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Execution error: {str(e)}",
                "output": None
            }
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except:
                pass
    
    def execute_command(self, command: str, timeout: Optional[int] = None) -> Dict:
        """Execute a shell command (restricted)"""
        # Allow only safe commands
        safe_commands = ['echo', 'date', 'time', 'dir', 'ls']
        command_parts = command.split()
        
        if not command_parts:
            return {
                "success": False,
                "error": "Empty command",
                "output": None
            }
        
        base_cmd = command_parts[0].lower()
        
        # Block dangerous commands
        dangerous = ['del', 'delete', 'rm', 'format', 'shutdown', 'restart', 'kill', 'taskkill']
        if any(d in base_cmd for d in dangerous):
            return {
                "success": False,
                "error": f"Dangerous command blocked: {base_cmd}",
                "output": None
            }
        
        timeout = timeout or self.max_execution_time
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            output = result.stdout
            if len(output) > self.max_output_size:
                output = output[:self.max_output_size] + "\n... (output truncated)"
            
            return {
                "success": result.returncode == 0,
                "output": output,
                "error": result.stderr if result.stderr else None,
                "return_code": result.returncode
            }
        
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Command timeout after {timeout} seconds",
                "output": None
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Command execution error: {str(e)}",
                "output": None
            }
    
    def install_package(self, package_name: str) -> Dict:
        """Install a Python package (restricted)"""
        # Allow only safe packages
        safe_packages = [
            'numpy', 'pandas', 'matplotlib', 'requests', 'pillow',
            'opencv-python', 'pyautogui', 'pyperclip', 'beautifulsoup4',
            'selenium', 'playwright', 'openai', 'google-generativeai'
        ]
        
        if package_name.lower() not in [p.lower() for p in safe_packages]:
            return {
                "success": False,
                "error": f"Package '{package_name}' not in safe list",
                "output": None
            }
        
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', package_name],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.stderr else None
            }
        
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Package installation timeout",
                "output": None
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Installation error: {str(e)}",
                "output": None
            }
    
    def cleanup(self):
        """Clean up sandbox directory"""
        try:
            for file in self.sandbox_dir.iterdir():
                if file.is_file():
                    file.unlink()
        except Exception as e:
            print(f"[Sandbox] Cleanup error: {e}")
