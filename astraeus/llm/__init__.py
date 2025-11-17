"""
LLM integration for intelligent agent reasoning.

This module provides interfaces to large language models for enhancing
agent decision-making with natural language understanding and chain-of-thought reasoning.
"""

from .llm_interface import LLMInterface, LLMProvider, LLMConfig, LLMResponse
from .prompt_templates import PromptTemplate, PromptLibrary
from .reasoning import ChainOfThoughtReasoning, ReasoningStep, ReasoningResult
from .few_shot import FewShotExample, FewShotLibrary

__all__ = [
    'LLMInterface',
    'LLMProvider',
    'LLMConfig',
    'LLMResponse',
    'PromptTemplate',
    'PromptLibrary',
    'ChainOfThoughtReasoning',
    'ReasoningStep',
    'ReasoningResult',
    'FewShotExample',
    'FewShotLibrary',
]
