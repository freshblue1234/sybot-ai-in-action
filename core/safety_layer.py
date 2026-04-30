"""
Safety and Control Layer for SYBOT
Provides comprehensive safety checks, risk classification, and action validation.
"""

import re
import ast
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from pathlib import Path
import json


class RiskLevel(Enum):
    """Risk levels for actions"""
    SAFE = "safe"  # No risk
    LOW = "low"  # Minimal risk
    MEDIUM = "medium"  # Requires confirmation
    HIGH = "high"  # Requires explicit approval
    CRITICAL = "critical"  # Blocked by default
    DANGEROUS = "dangerous"  # Never allowed


class ActionCategory(Enum):
    """Categories of actions"""
    FILE_OPERATION = "file_operation"
    SYSTEM_OPERATION = "system_operation"
    NETWORK_OPERATION = "network_operation"
    CODE_EXECUTION = "code_execution"
    APPLICATION_CONTROL = "application_control"
    DATA_ACCESS = "data_access"
    CONFIGURATION_CHANGE = "configuration_change"


@dataclass
class SafetyCheckResult:
    """Result of a safety check"""
    safe: bool
    risk_level: RiskLevel
    category: ActionCategory
    reason: str
    requires_confirmation: bool = False
    allowed: bool = True
    blocked: bool = False
    sandbox_required: bool = False


class SafetyLayer:
    """
    Comprehensive safety and control layer for SYBOT.
    Validates all actions before execution.
    """
    
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.safety_rules: Dict[ActionCategory, List[Callable]] = {}
        self.blocked_patterns: List[str] = []
        self.allowed_domains: List[str] = []
        self.sandboxed_operations: List[ActionCategory] = []
        
        # Load safety configuration
        self._load_config()
        self._init_default_rules()
    
    def _load_config(self):
        """Load safety configuration from file"""
        config_path = self.base_dir / "config" / "safety_config.json"
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
                self.blocked_patterns = config.get("blocked_patterns", [])
                self.allowed_domains = config.get("allowed_domains", [])
                self.sandboxed_operations = [
                    ActionCategory(cat) for cat in config.get("sandboxed_operations", [])
                ]
    
    def _init_default_rules(self):
        """Initialize default safety rules"""
        # File operation rules
        self.safety_rules[ActionCategory.FILE_OPERATION] = [
            self._check_file_destruction,
            self._check_system_files,
            self._check_sensitive_paths
        ]
        
        # System operation rules
        self.safety_rules[ActionCategory.SYSTEM_OPERATION] = [
            self._check_critical_system_ops,
            self._check_shutdown_restart
        ]
        
        # Network operation rules
        self.safety_rules[ActionCategory.NETWORK_OPERATION] = [
            self._check_blocked_domains,
            self._check_external_connections
        ]
        
        # Code execution rules
        self.safety_rules[ActionCategory.CODE_EXECUTION] = [
            self._check_dangerous_code,
            self._check_infinite_loops,
            self._check_file_access_in_code
        ]
        
        # Application control rules
        self.safety_rules[ActionCategory.APPLICATION_CONTROL] = [
            self._check_critical_applications
        ]
        
        # Data access rules
        self.safety_rules[ActionCategory.DATA_ACCESS] = [
            self._check_sensitive_data
        ]
        
        # Configuration change rules
        self.safety_rules[ActionCategory.CONFIGURATION_CHANGE] = [
            self._check_critical_configs
        ]
    
    def check_action(self, action: str, category: ActionCategory, 
                    context: Dict = None) -> SafetyCheckResult:
        """
        Perform comprehensive safety check on an action.
        
        Args:
            action: The action to check
            category: Category of the action
            context: Additional context
            
        Returns:
            SafetyCheckResult with detailed information
        """
        context = context or {}
        
        # Check blocked patterns first
        if self._is_blocked(action):
            return SafetyCheckResult(
                safe=False,
                risk_level=RiskLevel.DANGEROUS,
                category=category,
                reason="Action contains blocked pattern",
                blocked=True
            )
        
        # Run category-specific rules
        rules = self.safety_rules.get(category, [])
        for rule in rules:
            result = rule(action, context)
            if not result.safe:
                return result
        
        # Check if sandbox is required
        sandbox_required = category in self.sandboxed_operations
        
        return SafetyCheckResult(
            safe=True,
            risk_level=RiskLevel.LOW,
            category=category,
            reason="Action passed all safety checks",
            sandbox_required=sandbox_required
        )
    
    def _is_blocked(self, action: str) -> bool:
        """Check if action contains blocked patterns"""
        action_lower = action.lower()
        for pattern in self.blocked_patterns:
            if pattern.lower() in action_lower:
                return True
        return False
    
    # File operation rules
    def _check_file_destruction(self, action: str, context: Dict) -> SafetyCheckResult:
        """Check for file destruction operations"""
        destructive = ['delete', 'remove', 'erase', 'format', 'wipe', 'destroy']
        if any(d in action.lower() for d in destructive):
            return SafetyCheckResult(
                safe=True,
                risk_level=RiskLevel.HIGH,
                category=ActionCategory.FILE_OPERATION,
                reason="File destruction operation",
                requires_confirmation=True
            )
        return SafetyCheckResult(safe=True, risk_level=RiskLevel.LOW, 
                                category=ActionCategory.FILE_OPERATION, reason="")
    
    def _check_system_files(self, action: str, context: Dict) -> SafetyCheckResult:
        """Check for operations on system files"""
        system_paths = ['c:\\windows', 'c:\\program files', '/etc', '/usr/bin', '/system']
        action_lower = action.lower()
        for path in system_paths:
            if path.lower() in action_lower:
                return SafetyCheckResult(
                    safe=True,
                    risk_level=RiskLevel.CRITICAL,
                    category=ActionCategory.FILE_OPERATION,
                    reason="Operation on system file/directory",
                    requires_confirmation=True,
                    blocked=True
                )
        return SafetyCheckResult(safe=True, risk_level=RiskLevel.LOW,
                                category=ActionCategory.FILE_OPERATION, reason="")
    
    def _check_sensitive_paths(self, action: str, context: Dict) -> SafetyCheckResult:
        """Check for operations on sensitive paths"""
        sensitive = ['passwords', 'keys', 'secrets', 'credentials', '.ssh', '.aws']
        action_lower = action.lower()
        for path in sensitive:
            if path in action_lower:
                return SafetyCheckResult(
                    safe=True,
                    risk_level=RiskLevel.HIGH,
                    category=ActionCategory.FILE_OPERATION,
                    reason="Operation on sensitive path",
                    requires_confirmation=True
                )
        return SafetyCheckResult(safe=True, risk_level=RiskLevel.LOW,
                                category=ActionCategory.FILE_OPERATION, reason="")
    
    # System operation rules
    def _check_critical_system_ops(self, action: str, context: Dict) -> SafetyCheckResult:
        """Check for critical system operations"""
        critical = ['registry', 'services', 'drivers', 'kernel', 'boot']
        if any(c in action.lower() for c in critical):
            return SafetyCheckResult(
                safe=True,
                risk_level=RiskLevel.CRITICAL,
                category=ActionCategory.SYSTEM_OPERATION,
                reason="Critical system operation",
                requires_confirmation=True
            )
        return SafetyCheckResult(safe=True, risk_level=RiskLevel.LOW,
                                category=ActionCategory.SYSTEM_OPERATION, reason="")
    
    def _check_shutdown_restart(self, action: str, context: Dict) -> SafetyCheckResult:
        """Check for shutdown/restart operations"""
        shutdown = ['shutdown', 'restart', 'reboot', 'power off']
        if any(s in action.lower() for s in shutdown):
            return SafetyCheckResult(
                safe=True,
                risk_level=RiskLevel.CRITICAL,
                category=ActionCategory.SYSTEM_OPERATION,
                reason="System shutdown/restart operation",
                requires_confirmation=True
            )
        return SafetyCheckResult(safe=True, risk_level=RiskLevel.LOW,
                                category=ActionCategory.SYSTEM_OPERATION, reason="")
    
    # Network operation rules
    def _check_blocked_domains(self, action: str, context: Dict) -> SafetyCheckResult:
        """Check for blocked domains"""
        # Extract URLs from action
        url_pattern = r'https?://[^\s]+'
        urls = re.findall(url_pattern, action)
        
        for url in urls:
            domain = url.split('/')[2]
            if domain not in self.allowed_domains and self.allowed_domains:
                return SafetyCheckResult(
                    safe=True,
                    risk_level=RiskLevel.MEDIUM,
                    category=ActionCategory.NETWORK_OPERATION,
                    reason=f"Connection to non-whitelisted domain: {domain}",
                    requires_confirmation=True
                )
        
        return SafetyCheckResult(safe=True, risk_level=RiskLevel.LOW,
                                category=ActionCategory.NETWORK_OPERATION, reason="")
    
    def _check_external_connections(self, action: str, context: Dict) -> SafetyCheckResult:
        """Check for external network connections"""
        if 'http' in action.lower() or 'download' in action.lower():
            return SafetyCheckResult(
                safe=True,
                risk_level=RiskLevel.MEDIUM,
                category=ActionCategory.NETWORK_OPERATION,
                reason="External network connection",
                requires_confirmation=True
            )
        return SafetyCheckResult(safe=True, risk_level=RiskLevel.LOW,
                                category=ActionCategory.NETWORK_OPERATION, reason="")
    
    # Code execution rules
    def _check_dangerous_code(self, action: str, context: Dict) -> SafetyCheckResult:
        """Check for dangerous code patterns"""
        dangerous = ['os.system', 'subprocess.call', 'eval(', 'exec(',
                    '__import__', 'open(', 'file(']
        code_lower = action.lower()
        for pattern in dangerous:
            if pattern in code_lower:
                return SafetyCheckResult(
                    safe=True,
                    risk_level=RiskLevel.HIGH,
                    category=ActionCategory.CODE_EXECUTION,
                    reason=f"Code contains dangerous pattern: {pattern}",
                    sandbox_required=True
                )
        return SafetyCheckResult(safe=True, risk_level=RiskLevel.LOW,
                                category=ActionCategory.CODE_EXECUTION, reason="")
    
    def _check_infinite_loops(self, action: str, context: Dict) -> SafetyCheckResult:
        """Check for potential infinite loops"""
        if 'while true' in action.lower() or 'while 1' in action.lower():
            return SafetyCheckResult(
                safe=True,
                risk_level=RiskLevel.MEDIUM,
                category=ActionCategory.CODE_EXECUTION,
                reason="Code may contain infinite loop",
                sandbox_required=True
            )
        return SafetyCheckResult(safe=True, risk_level=RiskLevel.LOW,
                                category=ActionCategory.CODE_EXECUTION, reason="")
    
    def _check_file_access_in_code(self, action: str, context: Dict) -> SafetyCheckResult:
        """Check for file access in code"""
        file_ops = ['open(', 'write(', 'read(']
        if any(op in action.lower() for op in file_ops):
            return SafetyCheckResult(
                safe=True,
                risk_level=RiskLevel.MEDIUM,
                category=ActionCategory.CODE_EXECUTION,
                reason="Code performs file operations",
                sandbox_required=True
            )
        return SafetyCheckResult(safe=True, risk_level=RiskLevel.LOW,
                                category=ActionCategory.CODE_EXECUTION, reason="")
    
    # Application control rules
    def _check_critical_applications(self, action: str, context: Dict) -> SafetyCheckResult:
        """Check for control of critical applications"""
        critical = ['task manager', 'registry editor', 'command prompt', 'powershell',
                   'system config', 'services']
        if any(c in action.lower() for c in critical):
            return SafetyCheckResult(
                safe=True,
                risk_level=RiskLevel.HIGH,
                category=ActionCategory.APPLICATION_CONTROL,
                reason="Control of critical system application",
                requires_confirmation=True
            )
        return SafetyCheckResult(safe=True, risk_level=RiskLevel.LOW,
                                category=ActionCategory.APPLICATION_CONTROL, reason="")
    
    # Data access rules
    def _check_sensitive_data(self, action: str, context: Dict) -> SafetyCheckResult:
        """Check for access to sensitive data"""
        sensitive = ['password', 'api key', 'token', 'secret', 'credential',
                    'private key', 'credit card', 'ssn', 'social security']
        action_lower = action.lower()
        for term in sensitive:
            if term in action_lower:
                return SafetyCheckResult(
                    safe=True,
                    risk_level=RiskLevel.HIGH,
                    category=ActionCategory.DATA_ACCESS,
                    reason=f"Access to sensitive data: {term}",
                    requires_confirmation=True
                )
        return SafetyCheckResult(safe=True, risk_level=RiskLevel.LOW,
                                category=ActionCategory.DATA_ACCESS, reason="")
    
    # Configuration change rules
    def _check_critical_configs(self, action: str, context: Dict) -> SafetyCheckResult:
        """Check for changes to critical configurations"""
        critical = ['registry', 'hosts file', 'environment variables', 'path',
                   'startup', 'services', 'firewall']
        if any(c in action.lower() for c in critical):
            return SafetyCheckResult(
                safe=True,
                risk_level=RiskLevel.HIGH,
                category=ActionCategory.CONFIGURATION_CHANGE,
                reason="Change to critical system configuration",
                requires_confirmation=True
            )
        return SafetyCheckResult(safe=True, risk_level=RiskLevel.LOW,
                                category=ActionCategory.CONFIGURATION_CHANGE, reason="")
    
    def add_blocked_pattern(self, pattern: str):
        """Add a blocked pattern"""
        self.blocked_patterns.append(pattern)
    
    def add_allowed_domain(self, domain: str):
        """Add an allowed domain"""
        self.allowed_domains.append(domain)
    
    def add_sandboxed_category(self, category: ActionCategory):
        """Add a category that requires sandboxing"""
        self.sandboxed_operations.append(category)
    
    def add_custom_rule(self, category: ActionCategory, rule: Callable):
        """Add a custom safety rule for a category"""
        if category not in self.safety_rules:
            self.safety_rules[category] = []
        self.safety_rules[category].append(rule)
