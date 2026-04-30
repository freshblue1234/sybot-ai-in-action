"""
Model Provider Implementations for SYBOT
Supports Groq, OpenRouter, Ollama, HuggingFace, and Gemini
"""

import asyncio
import httpx
import json
from typing import Dict, List, Optional, Any, AsyncGenerator
from abc import ABC, abstractmethod
from dataclasses import dataclass
import time


@dataclass
class ModelResponse:
    """Standardized response from any model provider"""
    content: str
    model: str
    provider: str
    latency: float
    tokens_used: Optional[int] = None
    finish_reason: Optional[str] = None


class BaseModelProvider(ABC):
    """Abstract base class for all model providers"""
    
    def __init__(self, api_key: str, base_url: str = None, timeout: int = 30):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
    
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> ModelResponse:
        """Generate a response from the model"""
        pass
    
    @abstractmethod
    async def generate_stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """Generate a streaming response from the model"""
        pass
    
    @abstractmethod
    def get_headers(self) -> Dict[str, str]:
        """Get authentication headers for the provider"""
        pass


class GroqProvider(BaseModelProvider):
    """Groq API provider for fast inference"""
    
    def __init__(self, api_key: str, model: str = "llama3-70b-8192"):
        super().__init__(api_key, "https://api.groq.com/openai/v1", timeout=10)
        self.model = model
    
    def get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def generate(self, prompt: str, **kwargs) -> ModelResponse:
        start_time = time.time()
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4096)
        }
        
        response = await self.client.post(
            f"{self.base_url}/chat/completions",
            headers=self.get_headers(),
            json=payload
        )
        
        data = response.json()
        
        if response.status_code != 200:
            raise Exception(f"Groq API error: {data}")
        
        latency = time.time() - start_time
        content = data["choices"][0]["message"]["content"]
        
        return ModelResponse(
            content=content,
            model=self.model,
            provider="groq",
            latency=latency,
            tokens_used=data.get("usage", {}).get("total_tokens"),
            finish_reason=data["choices"][0].get("finish_reason")
        )
    
    async def generate_stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4096),
            "stream": True
        }
        
        async with self.client.post(
            f"{self.base_url}/chat/completions",
            headers=self.get_headers(),
            json=payload
        ) as response:
            async for line in response.content:
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]
                        if data_str == '[DONE]':
                            break
                        try:
                            data = json.loads(data_str)
                            if 'choices' in data and len(data['choices']) > 0:
                                delta = data['choices'][0].get('delta', {})
                                content = delta.get('content', '')
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue


class OpenRouterProvider(BaseModelProvider):
    """OpenRouter API provider for multi-model access"""
    
    def __init__(self, api_key: str, model: str = "mistralai/mistral-large-2402"):
        super().__init__(api_key, "https://openrouter.ai/api/v1", timeout=20)
        self.model = model
    
    def get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://sybot.ai",
            "X-Title": "SYBOT"
        }
    
    async def generate(self, prompt: str, **kwargs) -> ModelResponse:
        start_time = time.time()
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4096)
        }
        
        async with self.client.post(
            f"{self.base_url}/chat/completions",
            headers=self.get_headers(),
            json=payload
        ) as response:
            data = await response.json()
            
            if response.status_code != 200:
                raise Exception(f"OpenRouter API error: {data}")
            
            latency = time.time() - start_time
            content = data["choices"][0]["message"]["content"]
            
            return ModelResponse(
                content=content,
                model=self.model,
                provider="openrouter",
                latency=latency,
                tokens_used=data.get("usage", {}).get("total_tokens"),
                finish_reason=data["choices"][0].get("finish_reason")
            )
    
    async def generate_stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4096),
            "stream": True
        }
        
        async with self.client.post(
            f"{self.base_url}/chat/completions",
            headers=self.get_headers(),
            json=payload
        ) as response:
            async for line in response.content:
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]
                        if data_str == '[DONE]':
                            break
                        try:
                            data = json.loads(data_str)
                            if 'choices' in data and len(data['choices']) > 0:
                                delta = data['choices'][0].get('delta', {})
                                content = delta.get('content', '')
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue


class OllamaProvider(BaseModelProvider):
    """Ollama provider for local/offline inference"""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3"):
        super().__init__(None, base_url, timeout=60)
        self.model = model
    
    def get_headers(self) -> Dict[str, str]:
        return {"Content-Type": "application/json"}
    
    async def generate(self, prompt: str, **kwargs) -> ModelResponse:
        start_time = time.time()
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
                "num_predict": kwargs.get("max_tokens", 4096)
            }
        }
        
        async with self.client.post(
            f"{self.base_url}/api/generate",
            headers=self.get_headers(),
            json=payload
        ) as response:
            data = await response.json()
            
            if response.status_code != 200:
                raise Exception(f"Ollama API error: {data}")
            
            latency = time.time() - start_time
            content = data.get("response", "")
            
            return ModelResponse(
                content=content,
                model=self.model,
                provider="ollama",
                latency=latency,
                tokens_used=data.get("eval_count"),
                finish_reason=data.get("done_reason")
            )
    
    async def generate_stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
                "num_predict": kwargs.get("max_tokens", 4096)
            }
        }
        
        async with self.client.post(
            f"{self.base_url}/api/generate",
            headers=self.get_headers(),
            json=payload
        ) as response:
            async for line in response.content:
                if line:
                    try:
                        data = json.loads(line.decode('utf-8'))
                        if 'response' in data:
                            yield data['response']
                        if data.get('done'):
                            break
                    except json.JSONDecodeError:
                        continue


class HuggingFaceProvider(BaseModelProvider):
    """HuggingFace Inference API provider for special models"""
    
    def __init__(self, api_key: str, model: str = "google/vit-base-patch16-224"):
        super().__init__(api_key, "https://api-inference.huggingface.co/models", timeout=30)
        self.model = model
    
    def get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def generate(self, prompt: str, **kwargs) -> ModelResponse:
        start_time = time.time()
        
        # For text models
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": kwargs.get("max_tokens", 512),
                "temperature": kwargs.get("temperature", 0.7)
            }
        }
        
        async with self.client.post(
            f"{self.base_url}/{self.model}",
            headers=self.get_headers(),
            json=payload
        ) as response:
            data = await response.json()
            
            if response.status_code != 200:
                raise Exception(f"HuggingFace API error: {data}")
            
            latency = time.time() - start_time
            
            # Handle different response formats
            if isinstance(data, list):
                content = data[0].get("generated_text", "")
            elif isinstance(data, dict):
                content = data.get("generated_text", str(data))
            else:
                content = str(data)
            
            return ModelResponse(
                content=content,
                model=self.model,
                provider="huggingface",
                latency=latency
            )
    
    async def generate_stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        # HuggingFace streaming support varies by model
        response = await self.generate(prompt, **kwargs)
        yield response.content


class ModelProviderFactory:
    """Factory for creating model provider instances"""
    
    @staticmethod
    def create_provider(provider_type: str, api_key: str = None, 
                       base_url: str = None, model: str = None) -> BaseModelProvider:
        """Create a provider instance based on type"""
        
        if provider_type == "groq":
            return GroqProvider(api_key, model or "llama3-70b-8192")
        elif provider_type == "openrouter":
            return OpenRouterProvider(api_key, model or "mistralai/mistral-large-2402")
        elif provider_type == "ollama":
            return OllamaProvider(base_url or "http://localhost:11434", model or "llama3")
        elif provider_type == "huggingface":
            return HuggingFaceProvider(api_key, model or "google/vit-base-patch16-224")
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")


class MultiModelExecutor:
    """
    Executes requests across multiple models with intelligent routing and failover.
    """
    
    def __init__(self, router):
        self.router = router
        self.providers: Dict[str, BaseModelProvider] = {}
    
    async def execute(self, prompt: str, context: Dict = None, 
                     stream: bool = False) -> ModelResponse:
        """
        Execute a request with intelligent routing and failover.
        
        Args:
            prompt: User prompt
            context: Additional context (images, audio, etc.)
            stream: Whether to stream the response
            
        Returns:
            ModelResponse from the best available model
        """
        # Classify task
        task_type = self.router.classify_task(prompt, context)
        
        # Select model
        previous_failures = []
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                decision = self.router.select_model(task_type, previous_failures)
                print(f"[Router] Selected {decision.provider.value}/{decision.model_name} for {task_type.value}")
                
                # Get or create provider
                provider = self._get_provider(decision.provider, decision.model_name)
                
                # Execute request
                if stream:
                    # For streaming, return the generator
                    return provider.generate_stream(prompt)
                else:
                    response = await provider.generate(prompt)
                    
                    # Record performance
                    self.router.record_performance(
                        decision.provider,
                        decision.model_name,
                        success=True,
                        latency=response.latency
                    )
                    
                    return response
                    
            except Exception as e:
                print(f"[Router] Error with {decision.provider.value}: {e}")
                previous_failures.append(decision.provider)
                continue
        
        # All retries failed
        raise RuntimeError("All model providers failed to respond")
    
    def _get_provider(self, provider_type: str, model_name: str) -> BaseModelProvider:
        """Get or create a provider instance"""
        key = f"{provider_type}_{model_name}"
        
        if key not in self.providers:
            # Get model config
            model_config = None
            for config in self.router.models.values():
                if config.provider.value == provider_type and config.name == model_name:
                    model_config = config
                    break
            
            if not model_config:
                raise ValueError(f"Model config not found for {provider_type}/{model_name}")
            
            # Create provider
            provider = ModelProviderFactory.create_provider(
                provider_type,
                model_config.api_key,
                model_config.base_url,
                model_name
            )
            
            self.providers[key] = provider
        
        return self.providers[key]
    
    async def close(self):
        """Close all provider sessions"""
        for provider in self.providers.values():
            if provider.client:
                await provider.client.aclose()
