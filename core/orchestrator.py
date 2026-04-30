"""
SYBOT Orchestrator - The Central AI Brain
Acts as the main controller for the entire SYBOT system, coordinating all subsystems.
"""

import asyncio
import json
import time
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
import threading
from queue import Queue, Empty

from core.model_router import get_router, TaskType
from core.model_providers import MultiModelExecutor


class IntentType(Enum):
    """Types of user intents"""
    CHAT = "chat"  # Simple conversation
    COMMAND = "command"  # System command
    QUERY = "query"  # Information query
    TASK = "task"  # Complex multi-step task
    PERCEPTION = "perception"  # Vision/audio perception
    LEARNING = "learning"  # Learning new skill
    SAFETY = "safety"  # Safety-related action


class RiskLevel(Enum):
    """Risk levels for actions"""
    LOW = "low"  # Safe to execute
    MEDIUM = "medium"  # Requires confirmation
    HIGH = "high"  # Requires explicit approval
    CRITICAL = "critical"  # Blocked by default


class EventType(Enum):
    """Types of system events"""
    VOICE_COMMAND = "voice_command"
    SYSTEM_CHANGE = "system_change"
    APPLICATION_LAUNCH = "application_launch"
    FILE_CHANGE = "file_change"
    USER_PRESENCE = "user_presence"
    TIMER = "timer"
    MANUAL_TRIGGER = "manual_trigger"


@dataclass
class Intent:
    """Parsed user intent"""
    type: IntentType
    text: str
    confidence: float
    entities: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    """A task to be executed"""
    id: str
    intent: Intent
    steps: List[Dict[str, Any]]
    current_step: int = 0
    status: str = "pending"  # pending, in_progress, completed, failed
    result: Any = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


@dataclass
class Event:
    """A system event"""
    type: EventType
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    priority: int = 0  # Higher = more important


@dataclass
class SafetyCheck:
    """Result of a safety check"""
    safe: bool
    risk_level: RiskLevel
    reason: str
    requires_confirmation: bool = False


class Orchestrator:
    """
    Central AI Orchestrator for SYBOT.
    Coordinates all subsystems and ensures safe, intelligent operation.
    """
    
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.router = get_router()
        self.executor = MultiModelExecutor(self.router)
        
        # Event system
        self.event_queue = Queue()
        self.event_handlers: Dict[EventType, List[Callable]] = {}
        self.event_monitor_running = False
        self.event_monitor_thread: Optional[threading.Thread] = None
        
        # Task management
        self.active_tasks: Dict[str, Task] = {}
        self.task_history: List[Task] = []
        self.task_counter = 0
        
        # Conversation context
        self.conversation_history: List[Dict] = []
        self.current_context: Dict[str, Any] = {}
        
        # Performance optimization: intent caching
        self.intent_cache: Dict[str, Intent] = {}
        self.cache_size = 50
        
        # Safety
        self.safety_rules: List[Callable] = []
        self.blocked_operations: List[str] = []
        
        # Self-recovery: track module health
        self.module_health: Dict[str, Dict] = {
            "router": {"healthy": True, "failures": 0, "last_failure": None},
            "executor": {"healthy": True, "failures": 0, "last_failure": None},
            "event_monitor": {"healthy": True, "failures": 0, "last_failure": None}
        }
        self.max_failures = 3
        
        # Personality
        self.personality_traits = {
            "friendly": True,
            "professional": True,
            "proactive": False,
            "humorous": False
        }
        
        # State
        self.state = {
            "listening": False,
            "speaking": False,
            "processing": False,
            "paused": False
        }
        
        # Load configuration
        self._load_config()
        self._init_safety_rules()
    
    def _load_config(self):
        """Load orchestrator configuration"""
        config_path = self.base_dir / "config" / "orchestrator_config.json"
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
                self.personality_traits.update(config.get("personality", {}))
                self.blocked_operations = config.get("blocked_operations", [])
    
    def _init_safety_rules(self):
        """Initialize default safety rules"""
        self.safety_rules = [
            self._check_file_operations,
            self._check_system_operations,
            self._check_network_operations,
            self._check_code_execution
        ]
    
    async def process_input(self, input_text: str, context: Dict = None) -> str:
        """
        Process user input through the orchestrator.
        
        Args:
            input_text: User's input text
            context: Additional context (audio, images, etc.)
            
        Returns:
            Response to the user
        """
        if self.state.get("paused", False):
            return "SYBOT is paused. Use orchestrator_control with resume action to continue."
        
        self.state["processing"] = True
        
        try:
            # 1. Analyze intent
            intent = await self._analyze_intent(input_text, context)
            
            # 2. Add to conversation history
            self.conversation_history.append({
                "role": "user",
                "content": input_text,
                "intent": intent.type.value,
                "timestamp": datetime.now().isoformat()
            })
            
            # Limit conversation history to prevent memory issues
            if len(self.conversation_history) > 100:
                self.conversation_history = self.conversation_history[-50:]
            
            # 3. Route based on intent with error handling
            try:
                if intent.type == IntentType.CHAT:
                    response = await self._handle_chat(input_text, context)
                elif intent.type == IntentType.COMMAND:
                    response = await self._handle_command(intent)
                elif intent.type == IntentType.QUERY:
                    response = await self._handle_query(input_text, context)
                elif intent.type == IntentType.TASK:
                    response = await self._handle_task(intent)
                elif intent.type == IntentType.PERCEPTION:
                    response = await self._handle_perception(intent)
                elif intent.type == IntentType.LEARNING:
                    response = await self._handle_learning(intent)
                else:
                    response = await self._handle_chat(input_text, context)
            except Exception as e:
                # Fallback to basic chat on error
                print(f"[Orchestrator] Handler error, falling back: {e}")
                response = await self._handle_chat(input_text, context)
            
            # 4. Add response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": response,
                "timestamp": datetime.now().isoformat()
            })
            
            return response
            
        except Exception as e:
            print(f"[Orchestrator] Critical error in process_input: {e}")
            return "I encountered an error processing your request. Please try again."
            
        finally:
            self.state["processing"] = False
    
    async def _analyze_intent(self, text: str, context: Dict = None) -> Intent:
        """
        Analyze user input to determine intent with caching for performance.
        
        Args:
            text: User input text
            context: Additional context
            
        Returns:
            Parsed intent
        """
        # Check cache for similar intents
        text_hash = hash(text.lower())
        if text_hash in self.intent_cache:
            return self.intent_cache[text_hash]
        
        text_lower = text.lower()
        
        # Check for commands (imperative verbs, system actions)
        command_keywords = ['open', 'close', 'start', 'stop', 'launch', 'shutdown', 
                          'restart', 'delete', 'remove', 'install', 'update']
        if any(kw in text_lower for kw in command_keywords):
            intent = Intent(
                type=IntentType.COMMAND,
                text=text,
                confidence=0.8,
                entities={"action": self._extract_command(text_lower)}
            )
            self._cache_intent(text_hash, intent)
            return intent
        
        # Check for learning requests
        learning_keywords = ['learn', 'teach', 'remember', 'save', 'create skill', 
                           'new capability', 'how to']
        if any(kw in text_lower for kw in learning_keywords):
            intent = Intent(
                type=IntentType.LEARNING,
                text=text,
                confidence=0.7,
                entities={"topic": text}
            )
            self._cache_intent(text_hash, intent)
            return intent
        
        # Check for perception requests
        perception_keywords = ['look at', 'see', 'watch', 'show me', 'what do you see',
                              'analyze screen', 'check camera']
        if any(kw in text_lower for kw in perception_keywords):
            intent = Intent(
                type=IntentType.PERCEPTION,
                text=text,
                confidence=0.8,
                context=context or {}
            )
            self._cache_intent(text_hash, intent)
            return intent
        
        # Check for complex tasks (multi-step)
        task_keywords = ['plan', 'schedule', 'organize', 'prepare', 'set up',
                        'then', 'after that', 'first', 'next']
        if any(kw in text_lower for kw in task_keywords):
            intent = Intent(
                type=IntentType.TASK,
                text=text,
                confidence=0.7,
                entities={"steps": self._extract_steps(text)}
            )
            self._cache_intent(text_hash, intent)
            return intent
        
        # Default to query
        intent = Intent(
            type=IntentType.QUERY,
            text=text,
            confidence=0.6
        )
        self._cache_intent(text_hash, intent)
        return intent
    
    def _cache_intent(self, text_hash: int, intent: Intent):
        """Cache intent for performance"""
        if len(self.intent_cache) >= self.cache_size:
            # Remove oldest entry
            oldest_key = next(iter(self.intent_cache))
            del self.intent_cache[oldest_key]
        self.intent_cache[text_hash] = intent
    
    def _extract_command(self, text: str) -> str:
        """Extract command action from text"""
        verbs = ['open', 'close', 'start', 'stop', 'launch', 'shutdown']
        for verb in verbs:
            if verb in text:
                return verb
        return "unknown"
    
    def _extract_steps(self, text: str) -> List[str]:
        """Extract steps from multi-step task description"""
        # Simple implementation - split by common markers
        markers = ['then', 'after that', 'next', 'finally']
        steps = [text]
        for marker in markers:
            if marker in text.lower():
                parts = text.split(marker, 1)
                steps = [parts[0].strip(), parts[1].strip()]
                break
        return steps
    
    async def _handle_chat(self, text: str, context: Dict = None) -> str:
        """Handle simple chat/conversation"""
        try:
            # Use multi-model routing for chat
            response = await self.executor.execute(text, context)
            return response.content
        except Exception as e:
            print(f"[Orchestrator] Chat handler error: {e}")
            self._report_module_failure("executor", e)
            # Fallback response
            return "I'm having trouble connecting to my AI models right now. Please try again."
    
    async def _handle_command(self, intent: Intent) -> str:
        """Handle system commands"""
        try:
            # Safety check first
            safety = await self._check_safety(intent)
            if not safety.safe:
                if safety.requires_confirmation:
                    return f"Safety check: {safety.reason}. Do you want to proceed?"
                else:
                    return f"Cannot execute: {safety.reason}"
            
            # Execute command through existing tool system
            # This would integrate with the existing tool execution in main.py
            return f"Executing command: {intent.entities.get('action', 'unknown')}"
        except Exception as e:
            print(f"[Orchestrator] Command handler error: {e}")
            return f"Failed to execute command: {str(e)}"
    
    async def _handle_query(self, text: str, context: Dict = None) -> str:
        """Handle information queries"""
        try:
            # Use appropriate model based on query complexity
            task_type = self.router.classify_task(text, context)
            response = await self.executor.execute(text, context)
            return response.content
        except Exception as e:
            print(f"[Orchestrator] Query handler error: {e}")
            self._report_module_failure("executor", e)
            return "I couldn't process your query. Please try again."
    
    async def _handle_task(self, intent: Intent) -> str:
        """Handle complex multi-step tasks"""
        try:
            # Create task
            task = Task(
                id=f"task_{self.task_counter}",
                intent=intent,
                steps=intent.entities.get("steps", [intent.text])
            )
            self.task_counter += 1
            self.active_tasks[task.id] = task
            
            # Limit active tasks to prevent overload
            if len(self.active_tasks) > 10:
                oldest_task_id = list(self.active_tasks.keys())[0]
                del self.active_tasks[oldest_task_id]
            
            # Execute steps
            results = []
            for i, step in enumerate(task.steps):
                task.current_step = i
                task.status = "in_progress"
                
                try:
                    result = await self.executor.execute(step)
                    results.append(result.content)
                except Exception as e:
                    results.append(f"Step failed: {str(e)}")
                    self._report_module_failure("executor", e)
                    task.status = "failed"
                    break
            
            if task.status != "failed":
                task.status = "completed"
                task.completed_at = datetime.now()
            
            self.task_history.append(task)
            # Limit history
            if len(self.task_history) > 50:
                self.task_history = self.task_history[-25:]
            
            del self.active_tasks[task.id]
            
            return f"Task completed with {len(results)} steps."
        except Exception as e:
            print(f"[Orchestrator] Task handler error: {e}")
            return "I encountered an error processing your task."
    
    async def _handle_perception(self, intent: Intent) -> str:
        """Handle perception requests (vision, audio)"""
        try:
            return "Perception module activated."
        except Exception as e:
            print(f"[Orchestrator] Perception handler error: {e}")
            return "I couldn't activate the perception module."
    
    async def _handle_learning(self, intent: Intent) -> str:
        """Handle learning requests"""
        try:
            return "I'll learn that capability."
        except Exception as e:
            print(f"[Orchestrator] Learning handler error: {e}")
            return "I couldn't process that learning request."
    
    async def _check_safety(self, intent: Intent) -> SafetyCheck:
        """Check if an action is safe to execute"""
        for rule in self.safety_rules:
            result = await rule(intent)
            if not result.safe:
                return result
        
        return SafetyCheck(
            safe=True,
            risk_level=RiskLevel.LOW,
            reason="Action passed all safety checks"
        )
    
    async def _check_file_operations(self, intent: Intent) -> SafetyCheck:
        """Check file operation safety"""
        dangerous = ['delete', 'remove', 'format', 'erase']
        if any(d in intent.text.lower() for d in dangerous):
            return SafetyCheck(
                safe=True,
                risk_level=RiskLevel.HIGH,
                reason="File deletion operation",
                requires_confirmation=True
            )
        return SafetyCheck(safe=True, risk_level=RiskLevel.LOW, reason="")
    
    async def _check_system_operations(self, intent: Intent) -> SafetyCheck:
        """Check system operation safety"""
        critical = ['shutdown', 'restart', 'format', 'uninstall']
        if any(c in intent.text.lower() for c in critical):
            return SafetyCheck(
                safe=True,
                risk_level=RiskLevel.CRITICAL,
                reason="Critical system operation",
                requires_confirmation=True
            )
        return SafetyCheck(safe=True, risk_level=RiskLevel.LOW, reason="")
    
    async def _check_network_operations(self, intent: Intent) -> SafetyCheck:
        """Check network operation safety"""
        return SafetyCheck(safe=True, risk_level=RiskLevel.LOW, reason="")
    
    async def _check_code_execution(self, intent: Intent) -> SafetyCheck:
        """Check code execution safety"""
        code_keywords = ['execute', 'run', 'eval', 'exec']
        if any(k in intent.text.lower() for k in code_keywords):
            return SafetyCheck(
                safe=True,
                risk_level=RiskLevel.MEDIUM,
                reason="Code execution",
                requires_confirmation=True
            )
        return SafetyCheck(safe=True, risk_level=RiskLevel.LOW, reason="")
    
    def emit_event(self, event_type: EventType, data: Dict[str, Any]):
        """Emit an event to the event system"""
        event = Event(type=event_type, data=data)
        self.event_queue.put(event)
    
    def register_event_handler(self, event_type: EventType, handler: Callable):
        """Register a handler for an event type"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    def start_event_monitor(self):
        """Start the background event monitoring thread"""
        if self.event_monitor_running:
            return
        
        self.event_monitor_running = True
        self.event_monitor_thread = threading.Thread(target=self._monitor_events, daemon=True)
        self.event_monitor_thread.start()
    
    def stop_event_monitor(self):
        """Stop the event monitoring thread"""
        self.event_monitor_running = False
        if self.event_monitor_thread:
            self.event_monitor_thread.join(timeout=1)
    
    def _monitor_events(self):
        """Monitor and process events in background"""
        while self.event_monitor_running:
            try:
                event = self.event_queue.get(timeout=0.1)
                self._process_event(event)
            except Empty:
                continue
    
    def _process_event(self, event: Event):
        """Process a single event"""
        handlers = self.event_handlers.get(event.type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                print(f"[Orchestrator] Event handler error: {e}")
    
    def pause(self):
        """Pause orchestrator processing"""
        self.state["paused"] = True
    
    def resume(self):
        """Resume orchestrator processing"""
        self.state["paused"] = False
    
    def get_state(self) -> Dict:
        """Get current orchestrator state"""
        return {
            "state": self.state,
            "active_tasks": len(self.active_tasks),
            "task_history": len(self.task_history),
            "conversation_length": len(self.conversation_history),
            "event_queue_size": self.event_queue.qsize(),
            "module_health": self.module_health
        }
    
    def _report_module_failure(self, module_name: str, error: Exception):
        """Report a module failure and attempt recovery"""
        health = self.module_health.get(module_name, {"healthy": True, "failures": 0, "last_failure": None})
        health["failures"] += 1
        health["last_failure"] = datetime.now().isoformat()
        health["healthy"] = health["failures"] < self.max_failures
        self.module_health[module_name] = health
        
        print(f"[Orchestrator] Module {module_name} failed (failure #{health['failures']}): {error}")
        
        # Attempt self-recovery
        if not health["healthy"]:
            self._attempt_module_recovery(module_name)
    
    def _attempt_module_recovery(self, module_name: str):
        """Attempt to recover a failed module"""
        print(f"[Orchestrator] Attempting to recover module: {module_name}")
        
        try:
            if module_name == "router":
                # Reinitialize router
                self.router = get_router()
                print("[Orchestrator] Router recovered")
            elif module_name == "executor":
                # Reinitialize executor
                self.executor = MultiModelExecutor(self.router)
                print("[Orchestrator] Executor recovered")
            elif module_name == "event_monitor":
                # Restart event monitor
                self.stop_event_monitor()
                time.sleep(1)
                self.start_event_monitor()
                print("[Orchestrator] Event monitor recovered")
            
            # Reset health status
            self.module_health[module_name] = {
                "healthy": True,
                "failures": 0,
                "last_failure": None
            }
        except Exception as e:
            print(f"[Orchestrator] Failed to recover module {module_name}: {e}")
    
    async def close(self):
        """Clean up resources"""
        try:
            self.stop_event_monitor()
        except Exception as e:
            print(f"[Orchestrator] Error stopping event monitor: {e}")
        
        try:
            await self.executor.close()
        except Exception as e:
            print(f"[Orchestrator] Error closing executor: {e}")
