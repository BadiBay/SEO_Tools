"""
Google Gemini LLM Provider.
Поддерживает генерацию текста, Vision (анализ изображений) и генерацию изображений.
"""
import asyncio
import base64
import httpx
from app.integrations.base import BaseLLMProvider, LLMResponse
from app.config import settings


class GeminiProvider(BaseLLMProvider):
    """Провайдер Google Gemini API через google-genai SDK."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key
        self.model = model or "gemini-2.5-flash"
        self._client = None

    async def _ensure_configured(self):
        """Асинхронно получает настройки ключа из БД, если они не были переданы."""
        from app.utils.key_manager import KeyManager
        if not self.api_key:
            self.api_key = await KeyManager.get_active_key("gemini")
            db_model = await KeyManager.get_model("gemini")
            if db_model:
                self.model = db_model

    def _get_client(self):
        if self._client is None:
            if not self.api_key:
                raise ValueError("No active API key found for Gemini")
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
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
                # Считаем ключ "исчерпанным" или нерабочим при: 429, 503, 500, ssl, max retries, quota
                if any(err in error_msg for err in ["429", "quota", "exhausted", "503", "500", "ssl", "max retries", "unavailable"]):
                    await KeyManager.mark_key_exhausted("gemini", self.api_key)
                    
                    new_key = await KeyManager.get_active_key("gemini")
                    if not new_key or new_key == self.api_key:
                        raise RuntimeError("No more active Gemini API keys available.") from e
                        
                    self.api_key = new_key
                    self._client = None # Reset client to use new key
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
        from google.genai import types

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        if system_prompt:
            config.system_instruction = system_prompt

        async def _call():
            client = self._get_client()
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=self.model,
                contents=prompt,
                config=config,
            )
            return LLMResponse(
                text=response.text or "",
                model=self.model,
                input_tokens=getattr(response.usage_metadata, "prompt_token_count", 0) if getattr(response, "usage_metadata", None) else 0,
                output_tokens=getattr(response.usage_metadata, "candidates_token_count", 0) if getattr(response, "usage_metadata", None) else 0,
                finish_reason=str(response.candidates[0].finish_reason) if response.candidates else "",
                raw={"model": self.model},
            )
            
        return await self._execute_with_fallback(_call)

    async def analyze_image(
        self,
        image_url: str,
        prompt: str,
        **kwargs,
    ) -> LLMResponse:
        from google.genai import types

        async def _call():
            client = self._get_client()
            async with httpx.AsyncClient() as http:
                resp = await http.get(image_url, timeout=30)
                resp.raise_for_status()
                image_bytes = resp.content
                content_type = resp.headers.get("content-type", "image/jpeg")

            image_part = types.Part.from_bytes(data=image_bytes, mime_type=content_type)

            response = await asyncio.to_thread(
                client.models.generate_content,
                model=self.model,
                contents=[image_part, prompt],
            )

            return LLMResponse(
                text=response.text or "",
                model=self.model,
                input_tokens=getattr(response.usage_metadata, "prompt_token_count", 0) if getattr(response, "usage_metadata", None) else 0,
                output_tokens=getattr(response.usage_metadata, "candidates_token_count", 0) if getattr(response, "usage_metadata", None) else 0,
                raw={"model": self.model, "image_url": image_url},
            )
            
        return await self._execute_with_fallback(_call)

    async def generate_image(self, prompt: str, **kwargs) -> bytes:
        from google.genai import types

        async def _call():
            client = self._get_client()
            response = await asyncio.to_thread(
                client.models.generate_images,
                model="imagen-3.0-generate-002",
                prompt=prompt,
                config=types.GenerateImagesConfig(number_of_images=1),
            )

            if response.generated_images:
                return response.generated_images[0].image.image_bytes
            raise RuntimeError("Gemini did not return an image")
            
        return await self._execute_with_fallback(_call)
