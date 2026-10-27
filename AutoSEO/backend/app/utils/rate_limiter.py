"""
Rate Limiter и Batch Processor — утилиты для контроля скорости обращений к API/LLM.
Задержка 0.5–1 сек между итерациями, сбор в батчи.
"""
import asyncio
import time
import logging
from typing import TypeVar, Callable, Awaitable, Sequence
from dataclasses import dataclass

logger = logging.getLogger(__name__)

T = TypeVar("T")
R = TypeVar("R")


@dataclass
class RateLimitConfig:
    """Конфигурация rate limiting."""
    delay_seconds: float = 0.7  # задержка между запросами
    batch_size: int = 5  # размер батча
    max_retries: int = 3  # макс. повторов при ошибке
    retry_delay: float = 2.0  # задержка перед повтором


class RateLimiter:
    """
    Rate limiter для последовательных вызовов API.
    Гарантирует минимальную задержку между вызовами.
    """

    def __init__(self, delay_seconds: float = 0.7):
        self.delay = delay_seconds
        self._last_call_time: float = 0
        self._lock = asyncio.Lock()

    async def wait(self):
        """Дождаться, пока можно делать следующий запрос."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_call_time
            if elapsed < self.delay:
                await asyncio.sleep(self.delay - elapsed)
            self._last_call_time = time.monotonic()

    async def call(self, func: Callable[..., Awaitable[R]], *args, **kwargs) -> R:
        """Вызвать функцию с rate limiting."""
        await self.wait()
        return await func(*args, **kwargs)


async def process_in_batches(
    items: Sequence[T],
    processor: Callable[[T], Awaitable[R]],
    config: RateLimitConfig | None = None,
    on_progress: Callable[[int, int, str], Awaitable[None]] | None = None,
) -> list[R | Exception]:
    """
    Обработать элементы батчами с rate limiting и retry.

    Args:
        items: Элементы для обработки
        processor: Async-функция обработки одного элемента
        config: Конфигурация rate limiting
        on_progress: Callback для отчёта о прогрессе (processed, total, message)

    Returns:
        Список результатов (или Exception для неудачных)
    """
    if config is None:
        config = RateLimitConfig()

    rate_limiter = RateLimiter(config.delay_seconds)
    results: list[R | Exception] = []
    total = len(items)

    for batch_start in range(0, total, config.batch_size):
        batch = items[batch_start:batch_start + config.batch_size]

        for i, item in enumerate(batch):
            idx = batch_start + i
            result = None

            for attempt in range(config.max_retries):
                try:
                    result = await rate_limiter.call(processor, item)
                    break
                except Exception as e:
                    logger.warning(
                        f"Attempt {attempt + 1}/{config.max_retries} failed for item {idx}: {e}"
                    )
                    if attempt < config.max_retries - 1:
                        await asyncio.sleep(config.retry_delay * (attempt + 1))
                    else:
                        result = e

            results.append(result)

            if on_progress:
                await on_progress(
                    idx + 1, total,
                    f"Обработано {idx + 1} из {total}"
                )

        # Пауза между батчами
        if batch_start + config.batch_size < total:
            logger.info(f"Batch {batch_start // config.batch_size + 1} done, "
                        f"waiting before next batch...")
            await asyncio.sleep(config.delay_seconds * 2)

    return results
