"""
Mock LLM Provider — для разработки и тестирования без реальных API-ключей.
Возвращает реалистичные тестовые данные.
"""
import json
import random
from app.integrations.base import BaseLLMProvider, LLMResponse


class MockLLMProvider(BaseLLMProvider):
    """Заглушка LLM-провайдера с реалистичными ответами."""

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> LLMResponse:
        # Определяем тип запроса по ключевым словам и возвращаем адекватный ответ
        prompt_lower = prompt.lower()

        if "маркерн" in prompt_lower or "marker" in prompt_lower:
            text = json.dumps([
                "купить окна ПВХ москва",
                "пластиковые окна цена",
                "остекление балкона стоимость",
                "окна ПВХ от производителя",
                "замена окон в квартире",
                "установка пластиковых окон",
                "окна REHAU цена",
                "двухкамерный стеклопакет купить",
                "энергосберегающие окна москва",
                "окна в новостройку заказать",
            ], ensure_ascii=False)
        elif "конкурент" in prompt_lower or "competitor" in prompt_lower or "классифик" in prompt_lower:
            text = json.dumps({
                "is_competitor": random.choice([True, True, True, False]),
                "reason": "Компания предлагает аналогичные услуги в том же регионе",
                "confidence": round(random.uniform(0.7, 0.99), 2),
            }, ensure_ascii=False)
        elif "утп" in prompt_lower or "utp" in prompt_lower or "преимущ" in prompt_lower:
            text = json.dumps({
                "utps": [
                    "Собственное производство — цены на 15-20% ниже рынка",
                    "Гарантия 10 лет на профиль и монтаж",
                    "Бесплатный выезд замерщика в день обращения",
                ],
                "categories": [
                    "Пластиковые окна", "Балконы и лоджии",
                    "Входные двери", "Москитные сетки",
                ],
                "main_focus": "Коммерческий каталог услуг с калькулятором цен",
            }, ensure_ascii=False)
        elif "описан" in prompt_lower or "description" in prompt_lower or "тематик" in prompt_lower:
            text = "Компания по производству и установке пластиковых окон и дверей в Москве и области."
        elif "alt" in prompt_lower or "изображен" in prompt_lower:
            text = "Белое пластиковое окно с двумя створками в интерьере современной квартиры"
        else:
            text = f"[Mock LLM Response] Обработан запрос длиной {len(prompt)} символов. Сгенерирован тестовый ответ для разработки."

        return LLMResponse(
            text=text,
            model="mock-llm",
            input_tokens=len(prompt) // 4,
            output_tokens=len(text) // 4,
            finish_reason="stop",
            raw={"mock": True},
        )

    async def analyze_image(
        self,
        image_url: str,
        prompt: str,
        **kwargs,
    ) -> LLMResponse:
        # Vision mock
        if "тренд" in prompt.lower() or "видимост" in prompt.lower() or "график" in prompt.lower():
            trend = random.choice(["growth", "decline", "stagnation"])
            color = {"growth": "green", "decline": "red", "stagnation": "yellow"}[trend]
            text = json.dumps({
                "trend": trend,
                "color": color,
                "description": f"График показывает {'рост' if trend == 'growth' else 'падение' if trend == 'decline' else 'стагнацию'} видимости за последние 12 месяцев",
            }, ensure_ascii=False)
        else:
            text = f"[Mock Vision] Изображение: {image_url}. Содержит контент, связанный с тематикой сайта."

        return LLMResponse(
            text=text,
            model="mock-vision",
            input_tokens=100,
            output_tokens=len(text) // 4,
            raw={"mock": True, "image_url": image_url},
        )

    async def search_and_analyze(
        self,
        query: str,
        system_prompt: str = "",
        **kwargs,
    ) -> LLMResponse:
        return await self.generate_text(query, system_prompt)
