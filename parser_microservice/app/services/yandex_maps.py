import asyncio
import random
from typing import Optional
from loguru import logger
from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeoutError
from playwright_stealth import Stealth

from app.schemas.scraper import YandexMapCardRequest, YandexMapCardResponse


async def random_delay(min_seconds: float = 1.0, max_seconds: float = 3.0) -> None:
    """Имитация задержки человека между действиями."""
    delay = random.uniform(min_seconds, max_seconds)
    logger.debug(f"Ожидание {delay:.2f} сек...")
    await asyncio.sleep(delay)


async def parse_yandex_map_card(request: YandexMapCardRequest) -> YandexMapCardResponse:
    """
    Асинхронная функция для извлечения рейтинга и количества отзывов 
    из карточки организации на Яндекс Картах с использованием Playwright.
    """
    logger.info(f"Начало парсинга URL: {request.url}")
    
    async with Stealth().use_async(async_playwright()) as p:
        # Инициализация браузера
        # Для продакшена headless=True, для дебага headless=False
        browser = await p.chromium.launch(headless=True)
        
        # Создаем контекст со стандартным Viewport и User-Agent для мимикрии под обычного пользователя
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='ru-RU',
            timezone_id='Europe/Moscow'
        )
        
        page = await context.new_page()
        
        # Stealth-режим автоматически применяется к контексту благодаря Stealth().use_async()
        
        try:
            # Имитация: пользователь думает перед переходом
            await random_delay(1.0, 2.5)
            
            logger.info("Открытие страницы карточки...")
            # Переходим по URL, ожидаем загрузки DOM
            await page.goto(str(request.url), wait_until="domcontentloaded", timeout=30000)
            
            # Имитация: чтение контента и ожидание подгрузки JS/виджетов
            await random_delay(2.5, 4.5)
            
            logger.info(f"Страница загружена. Текущий URL: {page.url}")
            
            # --- БЛОК ОБРАБОТКИ КАПЧИ ---
            # TODO: Актуализировать CSS-селектор для SmartCaptcha Яндекса
            captcha_selector = ".captcha-container, iframe[src*='showcaptcha'], .CheckboxCaptcha" 
            if await page.locator(captcha_selector).count() > 0:
                logger.warning(f"Обнаружена капча на странице {request.url}")
                # Здесь в будущем будет логика вызова сервиса антикапчи
                return YandexMapCardResponse(
                    status="captcha",
                    error_message="Обнаружена капча (SmartCaptcha)"
                )

            # --- ИЗВЛЕЧЕНИЕ РЕЙТИНГА ---
            # TODO: Актуализировать CSS-селектор рейтинга (в Яндексе они часто меняют классы)
            rating_selector = ".business-rating-badge-view__rating-text, .business-header-rating-view__text"
            rating_val: Optional[float] = None
            
            try:
                # Ждем появления элемента рейтинга
                rating_element = await page.wait_for_selector(rating_selector, timeout=5000)
                if rating_element:
                    rating_text = await rating_element.inner_text()
                    # Парсим число с точкой/запятой
                    rating_val = float(rating_text.replace(',', '.').strip())
                    logger.debug(f"Извлечен рейтинг: {rating_val}")
            except PlaywrightTimeoutError:
                logger.warning("Селектор рейтинга не найден (Таймаут). Возможно, у организации нет рейтинга или изменилась верстка.")
            except ValueError:
                logger.warning("Не удалось распарсить значение рейтинга в число.")

            # Человеческая пауза перед следующим действием
            await random_delay(1.0, 2.0)

            # --- ИЗВЛЕЧЕНИЕ КОЛИЧЕСТВА ОЦЕНОК ---
            # TODO: Актуализировать CSS-селектор количества оценок/отзывов
            reviews_selector = ".business-rating-amount-view, .business-header-rating-view__text" 
            reviews_count: Optional[int] = None
            
            try:
                reviews_element = await page.wait_for_selector(reviews_selector, timeout=5000)
                if reviews_element:
                    reviews_text = await reviews_element.inner_text()
                    # Извлекаем все цифры из строки (например, "1 234 оценки" -> 1234)
                    digits = ''.join(filter(str.isdigit, reviews_text))
                    if digits:
                        reviews_count = int(digits)
                        logger.debug(f"Извлечено количество оценок: {reviews_count}")
            except PlaywrightTimeoutError:
                logger.warning("Селектор количества оценок не найден (Таймаут).")

            logger.success(f"Парсинг успешно завершен для {request.url}")
            return YandexMapCardResponse(
                rating=rating_val,
                reviews_count=reviews_count,
                status="success"
            )

        except PlaywrightTimeoutError as e:
            logger.error(f"Таймаут при парсинге {request.url}: {str(e)}")
            return YandexMapCardResponse(
                status="error",
                error_message="Таймаут ожидания страницы или элементов"
            )
        except Exception as e:
            logger.exception(f"Критическая ошибка при парсинге {request.url}: {str(e)}")
            return YandexMapCardResponse(
                status="error",
                error_message=str(e)
            )
        finally:
            # Небольшая задержка перед закрытием (как будто пользователь закрывает вкладку не моментально)
            await random_delay(0.5, 1.5)
            await context.close()
            await browser.close()
