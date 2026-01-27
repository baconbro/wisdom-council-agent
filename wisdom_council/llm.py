"""
Wisdom Council - LLM Client Implementations

Provides unified interfaces for different LLM providers.
"""

import os
from abc import ABC, abstractmethod
from typing import Optional


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


class OllamaClient(BaseLLMClient):
    """Client for Ollama local models."""

    def __init__(
        self,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        host: Optional[str] = None
    ):
        super().__init__(model, temperature, max_tokens)
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
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
