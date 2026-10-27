"""
LLM-адаптеры: Gemini, OpenAI, Perplexity, Mock.
Фабрика для создания провайдера по имени.
"""
from app.integrations.llm.base import BaseLLMProvider, LLMResponse
from app.integrations.llm.gemini import GeminiProvider
from app.integrations.llm.openai_provider import OpenAIProvider
from app.integrations.llm.perplexity import PerplexityProvider
from app.integrations.llm.mock import MockLLMProvider
from app.integrations.llm.factory import get_llm_provider

__all__ = [
    "BaseLLMProvider",
    "LLMResponse",
    "GeminiProvider",
    "OpenAIProvider",
    "PerplexityProvider",
    "MockLLMProvider",
    "get_llm_provider",
]
