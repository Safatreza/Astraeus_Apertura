"""
LLM interface for interacting with large language models.

Provides a unified interface for multiple LLM providers including
Anthropic Claude, OpenAI GPT, and local models.
"""

import os
import json
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from loguru import logger


class LLMProvider(Enum):
    """Supported LLM providers."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    LOCAL = "local"  # For locally hosted models (e.g., via Ollama)


@dataclass
class LLMConfig:
    """Configuration for LLM."""
    provider: LLMProvider = LLMProvider.ANTHROPIC
    model: str = "claude-3-5-sonnet-20241022"
    api_key: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 0.9
    timeout: int = 60
    base_url: Optional[str] = None  # For local models

    def __post_init__(self):
        """Load API key from environment if not provided."""
        if self.api_key is None:
            if self.provider == LLMProvider.ANTHROPIC:
                self.api_key = os.getenv('ANTHROPIC_API_KEY')
            elif self.provider == LLMProvider.OPENAI:
                self.api_key = os.getenv('OPENAI_API_KEY')


@dataclass
class LLMResponse:
    """Response from LLM."""
    content: str
    model: str
    usage: Dict[str, int] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def is_success(self) -> bool:
        """Check if response was successful."""
        return self.error is None


class LLMInterface(ABC):
    """
    Abstract interface for LLM providers.

    Subclasses implement specific providers (Anthropic, OpenAI, etc.)
    """

    def __init__(self, config: LLMConfig):
        """
        Initialize LLM interface.

        Args:
            config: LLM configuration
        """
        self.config = config
        logger.info(f"Initialized {config.provider.value} LLM interface with model {config.model}")

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate response from LLM.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt for context
            **kwargs: Additional provider-specific arguments

        Returns:
            LLMResponse object
        """
        pass

    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        response_schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate structured response (JSON).

        Args:
            prompt: User prompt
            response_schema: JSON schema for response
            system_prompt: Optional system prompt
            **kwargs: Additional arguments

        Returns:
            LLMResponse with JSON content
        """
        pass


class AnthropicLLM(LLMInterface):
    """Anthropic Claude LLM implementation."""

    def __init__(self, config: LLMConfig):
        """Initialize Anthropic client."""
        super().__init__(config)

        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=config.api_key)
        except ImportError:
            raise ImportError("anthropic package not installed. Install with: pip install anthropic")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response using Claude."""
        try:
            messages = [{"role": "user", "content": prompt}]

            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=kwargs.get('max_tokens', self.config.max_tokens),
                temperature=kwargs.get('temperature', self.config.temperature),
                system=system_prompt or "",
                messages=messages
            )

            return LLMResponse(
                content=response.content[0].text,
                model=response.model,
                usage={
                    'input_tokens': response.usage.input_tokens,
                    'output_tokens': response.usage.output_tokens,
                },
                metadata={'stop_reason': response.stop_reason}
            )

        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return LLMResponse(
                content="",
                model=self.config.model,
                error=str(e)
            )

    def generate_structured(
        self,
        prompt: str,
        response_schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate structured JSON response."""
        # Add JSON schema instructions to prompt
        schema_str = json.dumps(response_schema, indent=2)
        enhanced_prompt = f"""{prompt}

Please respond with valid JSON matching this schema:
{schema_str}

Respond ONLY with the JSON object, no additional text."""

        response = self.generate(enhanced_prompt, system_prompt, **kwargs)

        if response.is_success():
            try:
                # Extract JSON from response
                content = response.content.strip()

                # Try to find JSON in code blocks
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0].strip()
                elif '```' in content:
                    content = content.split('```')[1].split('```')[0].strip()

                # Parse JSON
                parsed = json.loads(content)
                response.content = json.dumps(parsed, indent=2)
                response.metadata['parsed_json'] = parsed

            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON response: {e}")
                response.error = f"Invalid JSON: {e}"

        return response


class OpenAILLM(LLMInterface):
    """OpenAI GPT LLM implementation."""

    def __init__(self, config: LLMConfig):
        """Initialize OpenAI client."""
        super().__init__(config)

        try:
            import openai
            self.client = openai.OpenAI(api_key=config.api_key)
        except ImportError:
            raise ImportError("openai package not installed. Install with: pip install openai")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response using GPT."""
        try:
            messages = []

            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                max_tokens=kwargs.get('max_tokens', self.config.max_tokens),
                temperature=kwargs.get('temperature', self.config.temperature),
                top_p=kwargs.get('top_p', self.config.top_p),
            )

            return LLMResponse(
                content=response.choices[0].message.content,
                model=response.model,
                usage={
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens,
                },
                metadata={'finish_reason': response.choices[0].finish_reason}
            )

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return LLMResponse(
                content="",
                model=self.config.model,
                error=str(e)
            )

    def generate_structured(
        self,
        prompt: str,
        response_schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate structured JSON response."""
        # OpenAI supports structured outputs via response_format
        try:
            messages = []

            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            schema_str = json.dumps(response_schema, indent=2)
            enhanced_prompt = f"""{prompt}

Respond with valid JSON matching this schema:
{schema_str}"""

            messages.append({"role": "user", "content": enhanced_prompt})

            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                max_tokens=kwargs.get('max_tokens', self.config.max_tokens),
                temperature=kwargs.get('temperature', self.config.temperature),
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content

            # Parse JSON
            try:
                parsed = json.loads(content)
                return LLMResponse(
                    content=json.dumps(parsed, indent=2),
                    model=response.model,
                    usage={
                        'prompt_tokens': response.usage.prompt_tokens,
                        'completion_tokens': response.usage.completion_tokens,
                    },
                    metadata={'parsed_json': parsed}
                )
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON response: {e}")
                return LLMResponse(
                    content=content,
                    model=response.model,
                    error=f"Invalid JSON: {e}"
                )

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return LLMResponse(
                content="",
                model=self.config.model,
                error=str(e)
            )


class LocalLLM(LLMInterface):
    """Local LLM implementation (e.g., via Ollama)."""

    def __init__(self, config: LLMConfig):
        """Initialize local LLM client."""
        super().__init__(config)

        self.base_url = config.base_url or "http://localhost:11434"

        try:
            import requests
            self.requests = requests
        except ImportError:
            raise ImportError("requests package not installed")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response using local model."""
        try:
            payload = {
                "model": self.config.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": kwargs.get('temperature', self.config.temperature),
                    "top_p": kwargs.get('top_p', self.config.top_p),
                }
            }

            if system_prompt:
                payload["system"] = system_prompt

            response = self.requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.config.timeout
            )

            response.raise_for_status()
            result = response.json()

            return LLMResponse(
                content=result.get('response', ''),
                model=self.config.model,
                metadata=result
            )

        except Exception as e:
            logger.error(f"Local LLM error: {e}")
            return LLMResponse(
                content="",
                model=self.config.model,
                error=str(e)
            )

    def generate_structured(
        self,
        prompt: str,
        response_schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate structured JSON response."""
        schema_str = json.dumps(response_schema, indent=2)
        enhanced_prompt = f"""{prompt}

Respond with valid JSON matching this schema:
{schema_str}

Respond ONLY with the JSON object."""

        response = self.generate(enhanced_prompt, system_prompt, **kwargs)

        if response.is_success():
            try:
                content = response.content.strip()

                # Extract JSON
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0].strip()
                elif '```' in content:
                    content = content.split('```')[1].split('```')[0].strip()

                parsed = json.loads(content)
                response.content = json.dumps(parsed, indent=2)
                response.metadata['parsed_json'] = parsed

            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON: {e}")
                response.error = f"Invalid JSON: {e}"

        return response


def create_llm(config: Optional[LLMConfig] = None) -> LLMInterface:
    """
    Factory function to create appropriate LLM instance.

    Args:
        config: LLM configuration (uses defaults if None)

    Returns:
        LLMInterface instance
    """
    if config is None:
        config = LLMConfig()

    if config.provider == LLMProvider.ANTHROPIC:
        return AnthropicLLM(config)
    elif config.provider == LLMProvider.OPENAI:
        return OpenAILLM(config)
    elif config.provider == LLMProvider.LOCAL:
        return LocalLLM(config)
    else:
        raise ValueError(f"Unknown LLM provider: {config.provider}")
