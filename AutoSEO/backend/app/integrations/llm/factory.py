"""
Фабрика LLM-провайдеров. Создаёт нужный провайдер по имени из конфига.
"""
from app.integrations.base import BaseLLMProvider
from app.config import settings


def get_llm_provider(provider_name: str | None = None) -> BaseLLMProvider:
    """
    Создать LLM-провайдер по имени.

    Args:
        provider_name: gemini | openai | anthropic | perplexity | mock
                       Если None — берётся из settings.default_llm_provider.
    """
    name = (provider_name or settings.default_llm_provider).lower()

    if name == "gemini":
        from app.integrations.llm.gemini import GeminiProvider
        return GeminiProvider()
    elif name == "openai":
        from app.integrations.llm.openai_provider import OpenAIProvider
        return OpenAIProvider()
    elif name == "perplexity":
        from app.integrations.llm.perplexity import PerplexityProvider
        return PerplexityProvider()
    elif name == "mock":
        from app.integrations.llm.mock import MockLLMProvider
        return MockLLMProvider()
    else:
        raise ValueError(f"Unknown LLM provider: {name}. "
                         f"Supported: gemini, openai, perplexity, mock")


def get_vision_provider() -> BaseLLMProvider:
    """Провайдер для Vision-задач (анализ изображений).
    
    Gemini по умолчанию. Ключ проверяется асинхронно при первом вызове
    через _ensure_configured() внутри провайдера. Если ключа нет —
    провайдер выбросит ошибку при попытке использования.
    """
    if settings.gemini_api_key:
        from app.integrations.llm.gemini import GeminiProvider
        return GeminiProvider()
    return get_llm_provider("mock")


def get_perplexity_provider() -> BaseLLMProvider:
    """Провайдер для задач с web-search (анализ УТП через Perplexity).
    
    Ключ проверяется из .env синхронно. Если Perplexity-ключ есть —
    используем его, иначе fallback на default LLM provider.
    """
    if settings.perplexity_api_key:
        from app.integrations.llm.perplexity import PerplexityProvider
        return PerplexityProvider()
    return get_llm_provider()  # Fallback на default
