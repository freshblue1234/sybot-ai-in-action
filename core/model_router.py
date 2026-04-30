"""
Multi-Model AI Router for SYBOT
Intelligently routes requests to the best AI model based on task type, speed, and availability.
"""

import asyncio
import json
import re
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path


class TaskType(Enum):
    """Classification of task types for routing"""
    FAST_CHAT = "fast_chat"  # Quick responses, simple queries
    COMPLEX_REASONING = "complex_reasoning"  # Deep analysis, long context
    CODE_GENERATION = "code_generation"  # Writing code
    VISION = "vision"  # Image analysis
    SPEECH = "speech"  # Audio processing
    OFFLINE = "offline"  # Private/local processing
    FALLBACK = "fallback"  # When primary models fail


class ModelProvider(Enum):
    """Available AI model providers"""
    GROQ = "groq"  # Fast real-time
    GEMINI = "gemini"  # Deep reasoning (Google AI Studio)
    OPENROUTER = "openrouter"  # Multi-model fallback
    OLLAMA = "ollama"  # Local/offline
    HUGGINGFACE = "huggingface"  # Special models


@dataclass
class ModelConfig:
    """Configuration for a model provider"""
    provider: ModelProvider
    name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    enabled: bool = True
    priority: int = 0  # Lower = higher priority
    supports: List[TaskType] = None
    max_tokens: int = 4096
    timeout: int = 30

    def __post_init__(self):
        if self.supports is None:
            self.supports = []


@dataclass
class RoutingDecision:
    """Result of routing decision"""
    provider: ModelProvider
    model_name: str
    reason: str
    confidence: float


class ModelRouter:
    """
    Intelligent model router that selects the best AI model for each task.
    Implements failover, load balancing, and task-aware routing.
    """

    def __init__(self, config_path: str = "config/model_config.json"):
        self.config_path = Path(config_path)
        self.models: Dict[str, ModelConfig] = {}
        self.routing_rules: Dict[TaskType, List[ModelProvider]] = {}
        self.failover_chain: List[ModelProvider] = []
        self.performance_stats: Dict[str, Dict] = {}
        self.load_config()
        self._init_routing_rules()

    def load_config(self):
        """Load model configurations from file and sync with API keys"""
        # Load API keys
        api_keys_path = Path("config/api_keys.json")
        api_keys = {}
        if api_keys_path.exists():
            with open(api_keys_path, 'r') as f:
                api_keys = json.load(f)
        
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                for model_id, model_data in config.get('models', {}).items():
                    # Sync API key from api_keys.json
                    provider = model_data['provider']
                    api_key = model_data.get('api_key')
                    
                    if not api_key:
                        if provider == 'groq':
                            api_key = api_keys.get('groq_api_key')
                        elif provider == 'openrouter':
                            api_key = api_keys.get('openrouter_api_key')
                        elif provider == 'huggingface':
                            api_key = api_keys.get('huggingface_api_key')
                        elif provider == 'gemini':
                            api_key = api_keys.get('gemini_api_key')
                    
                    self.models[model_id] = ModelConfig(
                        provider=ModelProvider(model_data['provider']),
                        name=model_data['name'],
                        api_key=api_key,
                        base_url=model_data.get('base_url'),
                        enabled=model_data.get('enabled', True),
                        priority=model_data.get('priority', 0),
                        supports=[TaskType(t) for t in model_data.get('supports', [])],
                        max_tokens=model_data.get('max_tokens', 4096),
                        timeout=model_data.get('timeout', 30)
                    )
        else:
            # Default configuration
            self._create_default_config(api_keys)

    def _create_default_config(self, api_keys: Dict = None):
        """Create default model configuration"""
        if api_keys is None:
            api_keys = {}
        
        self.models = {
            'groq_llama3': ModelConfig(
                provider=ModelProvider.GROQ,
                name='llama3-70b-8192',
                api_key=api_keys.get('groq_api_key'),
                priority=1,
                supports=[TaskType.FAST_CHAT, TaskType.CODE_GENERATION],
                timeout=10
            ),
            'gemini_pro': ModelConfig(
                provider=ModelProvider.GEMINI,
                name='gemini-2.0-flash-exp',
                api_key=api_keys.get('gemini_api_key'),
                priority=2,
                supports=[TaskType.COMPLEX_REASONING, TaskType.VISION, TaskType.SPEECH],
                timeout=30
            ),
            'openrouter_mixtral': ModelConfig(
                provider=ModelProvider.OPENROUTER,
                name='mistralai/mistral-large-2402',
                api_key=api_keys.get('openrouter_api_key'),
                priority=3,
                supports=[TaskType.FAST_CHAT, TaskType.COMPLEX_REASONING, TaskType.FALLBACK],
                timeout=20
            ),
            'ollama_llama3': ModelConfig(
                provider=ModelProvider.OLLAMA,
                name='llama3',
                priority=4,
                supports=[TaskType.OFFLINE, TaskType.FAST_CHAT],
                timeout=60,
                base_url='http://localhost:11434'
            ),
            'huggingface_vit': ModelConfig(
                provider=ModelProvider.HUGGINGFACE,
                name='google/vit-base-patch16-224',
                api_key=api_keys.get('huggingface_api_key'),
                priority=5,
                supports=[TaskType.VISION],
                timeout=30
            )
        }

    def _init_routing_rules(self):
        """Initialize routing rules based on task types"""
        self.routing_rules = {
            TaskType.FAST_CHAT: [
                ModelProvider.GROQ,
                ModelProvider.OLLAMA,
                ModelProvider.OPENROUTER,
                ModelProvider.GEMINI
            ],
            TaskType.COMPLEX_REASONING: [
                ModelProvider.GEMINI,
                ModelProvider.OPENROUTER,
                ModelProvider.GROQ
            ],
            TaskType.CODE_GENERATION: [
                ModelProvider.GROQ,
                ModelProvider.GEMINI,
                ModelProvider.OPENROUTER
            ],
            TaskType.VISION: [
                ModelProvider.GEMINI,
                ModelProvider.HUGGINGFACE,
                ModelProvider.OPENROUTER
            ],
            TaskType.SPEECH: [
                ModelProvider.GEMINI,
                ModelProvider.HUGGINGFACE
            ],
            TaskType.OFFLINE: [
                ModelProvider.OLLAMA
            ],
            TaskType.FALLBACK: [
                ModelProvider.OPENROUTER,
                ModelProvider.GROQ,
                ModelProvider.GEMINI
            ]
        }

        self.failover_chain = [
            ModelProvider.OPENROUTER,
            ModelProvider.GROQ,
            ModelProvider.GEMINI,
            ModelProvider.OLLAMA
        ]

    def classify_task(self, prompt: str, context: Dict = None) -> TaskType:
        """
        Analyze the prompt and classify the task type.
        
        Args:
            prompt: User input prompt
            context: Additional context (images, audio, etc.)
            
        Returns:
            TaskType enum value
        """
        prompt_lower = prompt.lower()
        
        # Check for vision/audio context
        if context and ('image' in context or 'images' in context):
            return TaskType.VISION
        if context and ('audio' in context or 'speech' in context):
            return TaskType.SPEECH
        
        # Check for code generation
        code_keywords = ['code', 'function', 'class', 'python', 'javascript', 
                        'programming', 'debug', 'implement', 'script']
        if any(kw in prompt_lower for kw in code_keywords):
            return TaskType.CODE_GENERATION
        
        # Check for complex reasoning
        reasoning_keywords = ['analyze', 'explain', 'compare', 'evaluate', 
                             'detailed', 'comprehensive', 'step by step',
                             'reasoning', 'complex', 'deep']
        if any(kw in prompt_lower for kw in reasoning_keywords):
            return TaskType.COMPLEX_REASONING
        
        # Check for offline/private request
        offline_keywords = ['offline', 'private', 'local', 'no internet']
        if any(kw in prompt_lower for kw in offline_keywords):
            return TaskType.OFFLINE
        
        # Default to fast chat
        return TaskType.FAST_CHAT

    def select_model(self, task_type: TaskType, 
                     previous_failures: List[ModelProvider] = None) -> RoutingDecision:
        """
        Select the best model for the given task type.
        
        Args:
            task_type: Type of task to perform
            previous_failures: List of providers that already failed
            
        Returns:
            RoutingDecision with selected model
        """
        if previous_failures is None:
            previous_failures = []
        
        # Get routing chain for this task type
        routing_chain = self.routing_rules.get(task_type, self.failover_chain)
        
        # Filter out failed providers and disabled models
        available_providers = [
            provider for provider in routing_chain
            if provider not in previous_failures
        ]
        
        # If all providers in chain failed, use failover chain
        if not available_providers:
            available_providers = [
                provider for provider in self.failover_chain
                if provider not in previous_failures
            ]
        
        # Find the best available model
        for provider in available_providers:
            model = self._get_best_model_for_provider(provider, task_type)
            if model and model.enabled:
                return RoutingDecision(
                    provider=provider,
                    model_name=model.name,
                    reason=f"Selected {provider.value} for {task_type.value}",
                    confidence=0.9
                )
        
        # Last resort: return any enabled model
        for model in self.models.values():
            if model.enabled and model.provider not in previous_failures:
                return RoutingDecision(
                    provider=model.provider,
                    model_name=model.name,
                    reason="Last resort selection",
                    confidence=0.5
                )
        
        raise RuntimeError("No available models for routing")

    def _get_best_model_for_provider(self, provider: ModelProvider, 
                                      task_type: TaskType) -> Optional[ModelConfig]:
        """Get the best model for a provider that supports the task type"""
        provider_models = [
            model for model in self.models.values()
            if model.provider == provider and task_type in model.supports
        ]
        
        if not provider_models:
            # Return any model from this provider
            provider_models = [
                model for model in self.models.values()
                if model.provider == provider
            ]
        
        if provider_models:
            # Sort by priority (lower = higher priority)
            provider_models.sort(key=lambda m: m.priority)
            return provider_models[0]
        
        return None

    def record_performance(self, provider: ModelProvider, 
                          model_name: str, success: bool, 
                          latency: float):
        """Record performance statistics for a model"""
        key = f"{provider.value}_{model_name}"
        if key not in self.performance_stats:
            self.performance_stats[key] = {
                'total_requests': 0,
                'successful_requests': 0,
                'failed_requests': 0,
                'total_latency': 0,
                'avg_latency': 0
            }
        
        stats = self.performance_stats[key]
        stats['total_requests'] += 1
        if success:
            stats['successful_requests'] += 1
        else:
            stats['failed_requests'] += 1
        stats['total_latency'] += latency
        stats['avg_latency'] = stats['total_latency'] / stats['total_requests']

    def get_performance_stats(self) -> Dict:
        """Get performance statistics for all models"""
        return self.performance_stats

    def save_config(self):
        """Save current configuration to file"""
        config = {
            'models': {}
        }
        for model_id, model in self.models.items():
            config['models'][model_id] = {
                'provider': model.provider.value,
                'name': model.name,
                'api_key': model.api_key,
                'base_url': model.base_url,
                'enabled': model.enabled,
                'priority': model.priority,
                'supports': [t.value for t in model.supports],
                'max_tokens': model.max_tokens,
                'timeout': model.timeout
            }
        
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)


# Singleton instance
_router_instance: Optional[ModelRouter] = None


def get_router() -> ModelRouter:
    """Get the singleton model router instance"""
    global _router_instance
    if _router_instance is None:
        _router_instance = ModelRouter()
    return _router_instance
