"""Реэкспорт базового класса из integrations.base для удобства импорта."""
from app.integrations.base import BaseLLMProvider, LLMResponse

__all__ = ["BaseLLMProvider", "LLMResponse"]
