"""
OpenAI LLM Provider.
Поддерживает GPT-4o/4.1 для текста и Vision.
"""
import httpx
import base64
from app.integrations.base import BaseLLMProvider, LLMResponse
from app.config import settings


class OpenAIProvider(BaseLLMProvider):
    """Провайдер OpenAI API."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key
        self.model = model or "gpt-4o"
        self._client = None

    async def _ensure_configured(self):
        """Асинхронно получает настройки ключа из БД, если они не были переданы."""
        from app.utils.key_manager import KeyManager
        if not self.api_key:
            self.api_key = await KeyManager.get_active_key("openai")
            db_model = await KeyManager.get_model("openai")
            if db_model:
                self.model = db_model

    def _get_client(self):
        if self._client is None:
            if not self.api_key:
                raise ValueError("No active API key found for OpenAI")
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client

    async def _execute_with_fallback(self, func, *args, **kwargs):
        """Выполняет функцию с автоматическим переключением ключей при ошибках (429, 503, SSL и др.)."""
        from app.utils.key_manager import KeyManager
        last_error = None
        
        for _ in range(3):
            await self._ensure_configured()
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_msg = str(e).lower()
                if any(err in error_msg for err in ["429", "quota", "exhausted", "503", "500", "ssl", "max retries", "unavailable", "insufficient_quota"]):
                    await KeyManager.mark_key_exhausted("openai", self.api_key)
                    
                    new_key = await KeyManager.get_active_key("openai")
                    if not new_key or new_key == self.api_key:
                        raise RuntimeError("No more active OpenAI API keys available.") from e
                        
                    self.api_key = new_key
                    self._client = None
                    last_error = e
                else:
                    raise e
                    
        raise last_error

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> LLMResponse:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async def _call():
            client = self._get_client()
            response = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            choice = response.choices[0]
            return LLMResponse(
                text=choice.message.content or "",
                model=self.model,
                input_tokens=response.usage.prompt_tokens if response.usage else 0,
                output_tokens=response.usage.completion_tokens if response.usage else 0,
                finish_reason=choice.finish_reason or "",
                raw={"model": self.model},
            )
            
        return await self._execute_with_fallback(_call)

    async def analyze_image(
        self,
        image_url: str,
        prompt: str,
        **kwargs,
    ) -> LLMResponse:
        async def _call():
            client = self._get_client()
            response = await client.chat.completions.create(
                model=self.model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }],
                max_tokens=1024,
            )

            choice = response.choices[0]
            return LLMResponse(
                text=choice.message.content or "",
                model=self.model,
                input_tokens=response.usage.prompt_tokens if response.usage else 0,
                output_tokens=response.usage.completion_tokens if response.usage else 0,
                raw={"model": self.model, "image_url": image_url},
            )
            
        return await self._execute_with_fallback(_call)
