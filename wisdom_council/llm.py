"""
Wisdom Council - LLM Client Implementations

Provides unified interfaces for different LLM providers.
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, AsyncGenerator


@dataclass
class StreamChunk:
    """A chunk of streamed LLM response."""
    content: str
    chunk_type: str  # "thinking", "content", "done"


class BaseLLMClient(ABC):
    """Base class for LLM clients."""

    def __init__(self, model: str, temperature: float = 0.7, max_tokens: int = 4096):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    @abstractmethod
    async def invoke(self, system_prompt: str, user_prompt: str) -> str:
        """
        Invoke the LLM with system and user prompts.

        Args:
            system_prompt: The system/instruction prompt
            user_prompt: The user's input prompt

        Returns:
            The LLM's response text
        """
        pass

    async def stream_invoke(
        self,
        system_prompt: str,
        user_prompt: str,
        enable_thinking: bool = False
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        Stream the LLM response with optional thinking.

        Default implementation falls back to non-streaming invoke.
        Override in subclasses for true streaming support.

        Args:
            system_prompt: The system/instruction prompt
            user_prompt: The user's input prompt
            enable_thinking: Whether to enable thinking/reasoning mode

        Yields:
            StreamChunk objects with content and chunk_type
        """
        # Default: fall back to non-streaming
        response = await self.invoke(system_prompt, user_prompt)
        yield StreamChunk(content=response, chunk_type="content")
        yield StreamChunk(content="", chunk_type="done")


class OllamaClient(BaseLLMClient):
    """Client for Ollama local models."""

    def __init__(
        self,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        host: Optional[str] = None,
        enable_thinking: bool = False
    ):
        super().__init__(model, temperature, max_tokens)
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.enable_thinking = enable_thinking
        self._client = None

    def _get_client(self):
        """Lazy initialization of Ollama client."""
        if self._client is None:
            import ollama
            self._client = ollama.AsyncClient(host=self.host)
        return self._client

    async def invoke(self, system_prompt: str, user_prompt: str) -> str:
        """Invoke Ollama model."""
        client = self._get_client()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response = await client.chat(
            model=self.model,
            messages=messages,
            options={
                "temperature": self.temperature,
                "num_predict": self.max_tokens
            }
        )

        return response["message"]["content"]

    async def stream_invoke(
        self,
        system_prompt: str,
        user_prompt: str,
        enable_thinking: bool = None
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        Stream Ollama response with optional thinking mode.

        When thinking is enabled, models that support it (like qwen3, deepseek-r1)
        will output their reasoning process before the final answer.

        Args:
            system_prompt: The system/instruction prompt
            user_prompt: The user's input prompt
            enable_thinking: Enable thinking mode (uses instance default if None)

        Yields:
            StreamChunk with chunk_type "thinking", "content", or "done"
        """
        client = self._get_client()

        # Use instance default if not specified
        if enable_thinking is None:
            enable_thinking = self.enable_thinking

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        options = {
            "temperature": self.temperature,
            "num_predict": self.max_tokens
        }

        # Enable thinking mode if requested
        if enable_thinking:
            options["think"] = True

        # Stream the response
        response_stream = await client.chat(
            model=self.model,
            messages=messages,
            options=options,
            stream=True
        )

        async for chunk in response_stream:
            message = chunk.get("message", {})
            content = message.get("content", "")

            if not content:
                continue

            # Determine chunk type based on thinking tag or message metadata
            # Ollama models with thinking output <think>...</think> tags
            # or have a "thinking" field in newer versions
            if message.get("thinking"):
                yield StreamChunk(content=content, chunk_type="thinking")
            elif "<think>" in content or "</think>" in content:
                # Handle inline thinking tags
                yield StreamChunk(content=content, chunk_type="thinking")
            else:
                yield StreamChunk(content=content, chunk_type="content")

            # Check if done
            if chunk.get("done"):
                yield StreamChunk(content="", chunk_type="done")
                break


class OpenAIClient(BaseLLMClient):
    """Client for OpenAI API."""

    def __init__(
        self,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        api_key: Optional[str] = None,
        organization: Optional[str] = None
    ):
        super().__init__(model, temperature, max_tokens)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.organization = organization or os.getenv("OPENAI_ORG_ID")
        self._client = None

    def _get_client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                organization=self.organization
            )
        return self._client

    async def invoke(self, system_prompt: str, user_prompt: str) -> str:
        """Invoke OpenAI model."""
        client = self._get_client()

        response = await client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )

        return response.choices[0].message.content


class AnthropicClient(BaseLLMClient):
    """Client for Anthropic API."""

    def __init__(
        self,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        api_key: Optional[str] = None
    ):
        super().__init__(model, temperature, max_tokens)
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self._client = None

    def _get_client(self):
        """Lazy initialization of Anthropic client."""
        if self._client is None:
            from anthropic import AsyncAnthropic
            self._client = AsyncAnthropic(api_key=self.api_key)
        return self._client

    async def invoke(self, system_prompt: str, user_prompt: str) -> str:
        """Invoke Anthropic model."""
        client = self._get_client()

        response = await client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ],
            temperature=self.temperature
        )

        return response.content[0].text
