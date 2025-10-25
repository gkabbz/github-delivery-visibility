#!/usr/bin/env python3
"""
LLM Client for interacting with language models.

Provides an abstract interface for LLM calls with concrete implementations
for different providers (Anthropic, OpenAI, etc.).
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import time
import os
from dataclasses import dataclass

from .config import DEFAULT_ANTHROPIC_MODEL, ANTHROPIC_PRICING


@dataclass
class LLMResponse:
    """Response from an LLM call."""

    content: str
    """The text response from the LLM."""

    model: str
    """The model used for the response."""

    input_tokens: int
    """Number of tokens in the input."""

    output_tokens: int
    """Number of tokens in the output."""

    cost_usd: float
    """Estimated cost in USD."""

    latency_seconds: float
    """Time taken for the request."""


class LLMClient(ABC):
    """Abstract interface for LLM clients."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 4096
    ) -> LLMResponse:
        """
        Generate a response from the LLM.

        Args:
            prompt: The user prompt/question
            system_prompt: Optional system instructions
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
            max_tokens: Maximum tokens to generate

        Returns:
            LLMResponse with content and metadata
        """
        pass


class AnthropicLLMClient(LLMClient):
    """
    Anthropic Claude client with retry logic and cost tracking.

    Pricing (as of Oct 2024):
    - Claude 3.5 Sonnet: $3/MTok input, $15/MTok output
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_ANTHROPIC_MODEL,
        max_retries: int = 3,
        retry_delay_seconds: float = 1.0
    ):
        """
        Initialize Anthropic client.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Model identifier
            max_retries: Number of retries on failure
            retry_delay_seconds: Initial delay between retries (exponential backoff)
        """
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError(
                "anthropic package not installed. "
                "Install with: pip install anthropic"
            )

        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Anthropic API key required. "
                "Set ANTHROPIC_API_KEY environment variable or pass api_key parameter."
            )

        self.model = model
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        self.client = Anthropic(api_key=self.api_key)

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 4096
    ) -> LLMResponse:
        """
        Generate a response using Claude with retry logic.

        Args:
            prompt: The user prompt/question
            system_prompt: Optional system instructions
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            LLMResponse with content and metadata

        Raises:
            Exception: If all retries fail
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                start_time = time.time()

                # Build request
                kwargs: Dict[str, Any] = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }

                if system_prompt:
                    kwargs["system"] = system_prompt

                # Make API call
                response = self.client.messages.create(**kwargs)

                # Calculate metrics
                latency = time.time() - start_time
                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens
                cost = self._calculate_cost(input_tokens, output_tokens)

                # Extract content
                content = response.content[0].text

                return LLMResponse(
                    content=content,
                    model=self.model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=cost,
                    latency_seconds=latency
                )

            except Exception as e:
                last_error = e

                # Don't retry on last attempt
                if attempt == self.max_retries - 1:
                    break

                # Exponential backoff
                delay = self.retry_delay_seconds * (2 ** attempt)
                time.sleep(delay)

        # All retries failed
        raise Exception(
            f"LLM request failed after {self.max_retries} attempts. "
            f"Last error: {last_error}"
        )

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost in USD for a request.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        if self.model not in ANTHROPIC_PRICING:
            # Default to Sonnet pricing if model not found
            pricing = ANTHROPIC_PRICING[DEFAULT_ANTHROPIC_MODEL]
        else:
            pricing = ANTHROPIC_PRICING[self.model]

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost
