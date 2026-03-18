"""LLM Adapter for Embeddings and Text Generation.

Provides a unified interface for both local (Ollama) and API-based
(OpenAI) language models. Handles embedding generation for course
recommendations and text generation for responses.

Configuration via environment variables:
    - LLM_PROVIDER: "ollama" or "openai"
    - LLM_MODEL: Model name (e.g., "all-minilm", "text-embedding-3-small")
    - LLM_API_KEY: API key for OpenAI
    - LLM_BASE_URL: Base URL for Ollama (default: http://localhost:11434)
    - LLM_TEMPERATURE: Generation temperature (default: 0.7)
    - LLM_MAX_TOKENS: Max tokens for generation (default: 500)

Usage:
    >>> from src.llm.adapter import LLMAdapter
    >>> llm = LLMAdapter()
    >>> 
    >>> # Generate embeddings
    >>> embedding = await llm.embed("Computer Science course description...")
    >>> 
    >>> # Generate text
    >>> response = await llm.generate(
    ...     prompt="Explain this course recommendation",
    ...     context={"course_name": "Computer Science", "reason": "High math match"}
    ... )
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np

from src.config import get_settings
from src.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class GenerationResult:
    """Result from text generation."""
    text: str
    tokens_used: int = 0
    model: str = ""
    finish_reason: Optional[str] = None


@dataclass
class EmbeddingResult:
    """Result from embedding generation."""
    embedding: List[float]
    dimensions: int = 0
    model: str = ""


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def embed(self, text: str) -> EmbeddingResult:
        """Generate embedding for text."""
        pass
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> GenerationResult:
        """Generate text from prompt."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if provider is healthy."""
        pass


class OllamaProvider(BaseLLMProvider):
    """Ollama local LLM provider.
    
    Uses local Ollama instance for embeddings and generation.
    Requires Ollama to be running locally.
    
    Default model for embeddings: "all-minilm" (384 dims)
    Default model for generation: "llama2" or "mistral"
    
    Environment:
        - LLM_BASE_URL: Ollama URL (default: http://localhost:11434)
        - LLM_MODEL: Model name for embeddings
        - LLM_CHAT_MODEL: Model name for generation
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        embed_model: Optional[str] = None,
        chat_model: Optional[str] = None,
    ):
        """Initialize Ollama provider.
        
        Args:
            base_url: Ollama base URL
            embed_model: Model for embeddings
            chat_model: Model for text generation
        """
        self.base_url = base_url or os.getenv("LLM_BASE_URL", "http://localhost:11434")
        self.embed_model = embed_model or os.getenv("LLM_MODEL", "all-minilm")
        self.chat_model = chat_model or os.getenv("LLM_CHAT_MODEL", "mistral")
        
        # Ensure base_url doesn't end with /
        self.base_url = self.base_url.rstrip("/")
        
        self._client: Optional[Any] = None
    
    def _get_client(self):
        """Get or create HTTP client."""
        if self._client is None:
            import httpx
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client
    
    async def embed(self, text: str) -> EmbeddingResult:
        """Generate embedding using Ollama.
        
        Args:
            text: Text to embed
        
        Returns:
            EmbeddingResult with 384-dimensional vector
        """
        client = self._get_client()
        
        try:
            response = await client.post(
                f"{self.base_url}/api/embeddings",
                json={
                    "model": self.embed_model,
                    "prompt": text,
                },
            )
            response.raise_for_status()
            
            data = response.json()
            embedding = data.get("embedding", [])
            
            # Ensure 384 dimensions (pad or truncate if necessary)
            embedding = self._normalize_embedding(embedding)
            
            return EmbeddingResult(
                embedding=embedding,
                dimensions=len(embedding),
                model=self.embed_model,
            )
            
        except Exception as exc:
            logger.error("Ollama embed failed", error=str(exc))
            # Return deterministic fallback embedding
            return self._fallback_embed(text)
    
    async def generate(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> GenerationResult:
        """Generate text using Ollama.
        
        Args:
            prompt: Generation prompt
            context: Optional context dictionary
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
        
        Returns:
            GenerationResult with generated text
        """
        client = self._get_client()
        
        # Format prompt with context
        formatted_prompt = self._format_prompt(prompt, context)
        
        temp = temperature or float(os.getenv("LLM_TEMPERATURE", "0.7"))
        max_tok = max_tokens or int(os.getenv("LLM_MAX_TOKENS", "500"))
        
        try:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.chat_model,
                    "prompt": formatted_prompt,
                    "stream": False,
                    "options": {
                        "temperature": temp,
                        "num_predict": max_tok,
                    },
                },
            )
            response.raise_for_status()
            
            data = response.json()
            generated_text = data.get("response", "")
            
            return GenerationResult(
                text=generated_text,
                tokens_used=data.get("eval_count", 0),
                model=self.chat_model,
                finish_reason="stop" if not data.get("done", False) else None,
            )
            
        except Exception as exc:
            logger.error("Ollama generate failed", error=str(exc))
            return GenerationResult(
                text="Error generating response. Please try again.",
                model=self.chat_model,
            )
    
    async def health_check(self) -> bool:
        """Check if Ollama is accessible."""
        client = self._get_client()
        
        try:
            response = await client.get(f"{self.base_url}/api/tags", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False
    
    def _format_prompt(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]],
    ) -> str:
        """Format prompt with context."""
        if not context:
            return prompt
        
        # Add context as system message
        context_str = "\n".join(f"{k}: {v}" for k, v in context.items())
        
        return f"""Context:
{context_str}

Instruction: {prompt}

Response:"""
    
    def _normalize_embedding(self, embedding: List[float]) -> List[float]:
        """Normalize embedding to 384 dimensions."""
        target_dim = 384
        current_dim = len(embedding)
        
        if current_dim == target_dim:
            return embedding
        
        if current_dim > target_dim:
            # Truncate
            return embedding[:target_dim]
        
        # Pad with zeros
        return embedding + [0.0] * (target_dim - current_dim)
    
    def _fallback_embed(self, text: str) -> EmbeddingResult:
        """Generate deterministic fallback embedding."""
        # Simple hash-based embedding for fallback
        import hashlib
        
        hash_bytes = hashlib.sha256(text.encode()).digest()
        
        # Generate 384-dimensional embedding from hash
        embedding = []
        for i in range(384):
            byte_val = hash_bytes[i % len(hash_bytes)]
            # Normalize to [-1, 1]
            val = (byte_val / 255.0) * 2 - 1
            # Add variation based on position
            val += 0.1 * np.sin(i * 0.1)
            embedding.append(float(np.clip(val, -1, 1)))
        
        # L2 normalize
        vec = np.array(embedding)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        
        return EmbeddingResult(
            embedding=vec.tolist(),
            dimensions=384,
            model=f"{self.embed_model}-fallback",
        )


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider.
    
    Uses OpenAI API for embeddings and generation.
    Requires OPENAI_API_KEY environment variable.
    
    Default embedding model: "text-embedding-3-small" (1536 dims, reduced to 384)
    Default chat model: "gpt-3.5-turbo"
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        embed_model: Optional[str] = None,
        chat_model: Optional[str] = None,
    ):
        """Initialize OpenAI provider.
        
        Args:
            api_key: OpenAI API key
            embed_model: Model for embeddings
            chat_model: Model for text generation
        """
        settings = get_settings()
        
        self.api_key = api_key or os.getenv("LLM_API_KEY") or settings.openai_api_key
        self.embed_model = embed_model or os.getenv("LLM_MODEL", "text-embedding-3-small")
        self.chat_model = chat_model or os.getenv("LLM_CHAT_MODEL", "gpt-3.5-turbo")
        
        self._client: Optional[Any] = None
    
    def _get_client(self):
        """Get or create OpenAI client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=self.api_key)
            except ImportError:
                raise RuntimeError("OpenAI package not installed. Install with: pip install openai")
        return self._client
    
    async def embed(self, text: str) -> EmbeddingResult:
        """Generate embedding using OpenAI.
        
        Args:
            text: Text to embed
        
        Returns:
            EmbeddingResult with normalized 384-dimensional vector
        """
        client = self._get_client()
        
        try:
            response = await client.embeddings.create(
                model=self.embed_model,
                input=text,
            )
            
            embedding = response.data[0].embedding
            
            # Reduce to 384 dimensions if necessary
            embedding = self._reduce_dimensions(embedding)
            
            return EmbeddingResult(
                embedding=embedding,
                dimensions=len(embedding),
                model=self.embed_model,
            )
            
        except Exception as exc:
            logger.error("OpenAI embed failed", error=str(exc))
            # Return fallback
            return self._fallback_embed(text)
    
    async def generate(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> GenerationResult:
        """Generate text using OpenAI.
        
        Args:
            prompt: Generation prompt
            context: Optional context dictionary
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
        
        Returns:
            GenerationResult with generated text
        """
        client = self._get_client()
        
        # Build messages
        messages = []
        
        if context:
            context_str = "\n".join(f"{k}: {v}" for k, v in context.items())
            messages.append({
                "role": "system",
                "content": f"Use the following context to answer:\n{context_str}",
            })
        
        messages.append({"role": "user", "content": prompt})
        
        temp = temperature or float(os.getenv("LLM_TEMPERATURE", "0.7"))
        max_tok = max_tokens or int(os.getenv("LLM_MAX_TOKENS", "500"))
        
        try:
            response = await client.chat.completions.create(
                model=self.chat_model,
                messages=messages,
                temperature=temp,
                max_tokens=max_tok,
            )
            
            choice = response.choices[0]
            
            return GenerationResult(
                text=choice.message.content or "",
                tokens_used=response.usage.total_tokens if response.usage else 0,
                model=self.chat_model,
                finish_reason=choice.finish_reason,
            )
            
        except Exception as exc:
            logger.error("OpenAI generate failed", error=str(exc))
            return GenerationResult(
                text="Error generating response. Please try again.",
                model=self.chat_model,
            )
    
    async def health_check(self) -> bool:
        """Check if OpenAI API is accessible."""
        if not self.api_key:
            return False
        
        try:
            # Try a simple embedding request
            await self.embed("test")
            return True
        except Exception:
            return False
    
    def _reduce_dimensions(self, embedding: List[float]) -> List[float]:
        """Reduce embedding dimensions to 384."""
        target_dim = 384
        current_dim = len(embedding)
        
        if current_dim == target_dim:
            return embedding
        
        if current_dim < target_dim:
            # Pad with zeros (unlikely for OpenAI)
            return embedding + [0.0] * (target_dim - current_dim)
        
        # Reduce dimensions using averaging
        # Split into 384 groups and average each group
        group_size = current_dim // target_dim
        reduced = []
        
        for i in range(target_dim):
            start = i * group_size
            end = start + group_size
            group = embedding[start:end]
            reduced.append(sum(group) / len(group))
        
        return reduced
    
    def _fallback_embed(self, text: str) -> EmbeddingResult:
        """Generate deterministic fallback embedding."""
        import hashlib
        
        hash_bytes = hashlib.sha256(text.encode()).digest()
        
        embedding = []
        for i in range(384):
            byte_val = hash_bytes[i % len(hash_bytes)]
            val = (byte_val / 255.0) * 2 - 1
            val += 0.1 * np.sin(i * 0.1)
            embedding.append(float(np.clip(val, -1, 1)))
        
        vec = np.array(embedding)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        
        return EmbeddingResult(
            embedding=vec.tolist(),
            dimensions=384,
            model=f"{self.embed_model}-fallback",
        )


class LLMAdapter:
    """Unified LLM adapter for embeddings and generation.
    
    Automatically selects provider based on environment configuration.
    Provides consistent interface regardless of backend.
    
    Configuration (environment variables):
        - LLM_PROVIDER: "ollama" or "openai" (default: "ollama")
        - LLM_MODEL: Embedding model name
        - LLM_CHAT_MODEL: Generation model name
        - LLM_API_KEY: API key for OpenAI
        - LLM_BASE_URL: Base URL for Ollama
    
    Example:
        >>> llm = LLMAdapter()
        >>> 
        >>> # Generate embedding
        >>> result = await llm.embed("Computer Science fundamentals")
        >>> print(f"Embedding dimensions: {result.dimensions}")
        >>> 
        >>> # Generate text
        >>> response = await llm.generate(
        ...     "Why is this course recommended?",
        ...     context={"course": "Computer Science", "match": "95%"}
        ... )
        >>> print(response.text)
    """
    
    def __init__(
        self,
        provider: Optional[str] = None,
        embed_model: Optional[str] = None,
        chat_model: Optional[str] = None,
    ):
        """Initialize LLM adapter.
        
        Args:
            provider: LLM provider ("ollama" or "openai")
            embed_model: Model for embeddings
            chat_model: Model for generation
        """
        self.provider_name = (provider or os.getenv("LLM_PROVIDER", "ollama")).lower()
        self.embed_model = embed_model or os.getenv("LLM_MODEL")
        self.chat_model = chat_model or os.getenv("LLM_CHAT_MODEL")
        
        # Initialize provider
        if self.provider_name == "openai":
            self._provider: BaseLLMProvider = OpenAIProvider(
                embed_model=self.embed_model,
                chat_model=self.chat_model,
            )
        elif self.provider_name == "ollama":
            self._provider = OllamaProvider(
                embed_model=self.embed_model,
                chat_model=self.chat_model,
            )
        else:
            raise ValueError(f"Unknown provider: {self.provider_name}")
        
        logger.info(
            "LLM adapter initialized",
            provider=self.provider_name,
            embed_model=self.embed_model or "default",
            chat_model=self.chat_model or "default",
        )
    
    async def embed(self, text: str) -> EmbeddingResult:
        """Generate embedding for text.
        
        Args:
            text: Text to embed
        
        Returns:
            EmbeddingResult with 384-dimensional vector
        """
        return await self._provider.embed(text)
    
    async def embed_batch(self, texts: List[str]) -> List[EmbeddingResult]:
        """Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
        
        Returns:
            List of EmbeddingResult
        """
        results = []
        for text in texts:
            result = await self.embed(text)
            results.append(result)
        return results
    
    async def generate(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> GenerationResult:
        """Generate text from prompt.
        
        Args:
            prompt: Generation prompt
            context: Optional context dictionary
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
        
        Returns:
            GenerationResult with generated text
        """
        return await self._provider.generate(
            prompt=prompt,
            context=context,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    
    async def health_check(self) -> bool:
        """Check if LLM provider is healthy."""
        return await self._provider.health_check()
    
    def get_provider_name(self) -> str:
        """Get the name of the current provider."""
        return self.provider_name
    
    def create_student_preference_embedding(
        self,
        interests: Dict[str, float],
        career_goal: str,
    ) -> List[float]:
        """Create a deterministic embedding from student preferences.
        
        This is useful for testing and when LLM is not available.
        Creates a 384-dimensional embedding based on preferences.
        
        Args:
            interests: Dict of interest areas with weights (e.g., {"math": 0.9})
            career_goal: Career goal string
        
        Returns:
            384-dimensional embedding vector
        """
        import hashlib
        
        # Combine interests and career goal into a string representation
        interest_str = ",".join(f"{k}:{v:.2f}" for k, v in sorted(interests.items()))
        combined = f"{interest_str}|career:{career_goal}"
        
        # Generate deterministic embedding
        hash_bytes = hashlib.sha256(combined.encode()).digest()
        
        embedding = []
        for i in range(384):
            # Use multiple hash bytes for better distribution
            byte_idx = i % len(hash_bytes)
            byte_val = hash_bytes[byte_idx]
            
            # Add interest-based signals in specific regions
            if i < 96 and "math" in interests:
                byte_val = int(byte_val * (0.5 + 0.5 * interests["math"]))
            elif i < 192 and "humanities" in interests:
                byte_val = int(byte_val * (0.5 + 0.5 * interests["humanities"]))
            
            # Normalize to [-1, 1]
            val = (byte_val / 255.0) * 2 - 1
            # Add smooth variation
            val += 0.05 * np.sin(i * 0.05)
            embedding.append(float(np.clip(val, -1, 1)))
        
        # L2 normalize
        vec = np.array(embedding)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        
        return vec.tolist()
