import asyncio
import random
from datetime import datetime, timezone
from typing import Optional, List
import dateparser
from loguru import logger
from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeoutError
from playwright_stealth import Stealth

from app.schemas.scraper import ReviewMonitorRequest, ReviewMonitorResponse, ReviewModel


async def random_delay(min_seconds: float = 1.0, max_seconds: float = 3.0) -> None:
    """Имитация задержки человека между действиями."""
    delay = random.uniform(min_seconds, max_seconds)
    logger.debug(f"Ожидание {delay:.2f} сек...")
    await asyncio.sleep(delay)


def parse_russian_date(date_str: str) -> Optional[datetime]:
    """Умный парсинг даты из строки (на русском)."""
    try:
        # Указываем timezone как UTC для стандартизации
        # dateparser умеет понимать "3 дня назад", "вчера", "12 апреля" и т.д.
        dt = dateparser.parse(
            date_str,
            languages=['ru'],
            settings={'TIMEZONE': 'UTC', 'RETURN_AS_TIMEZONE_AWARE': True}
        )
        return dt
    except Exception as e:
        logger.warning(f"Не удалось распарсить дату '{date_str}': {e}")
        return None


async def parse_reviews_monitor(request: ReviewMonitorRequest) -> ReviewMonitorResponse:
    """
    Парсинг новых отзывов с геосервиса.
    """
    logger.info(f"Начало мониторинга отзывов: {request.url}, last_check_date: {request.last_check_date}")
    
    # Парсим last_check_date из строки (приходит в ISO формате из Pydantic)
    try:
        last_check_dt = datetime.fromisoformat(request.last_check_date.replace("Z", "+00:00"))
        # Убедимся, что дата timezone-aware для корректного сравнения
        if last_check_dt.tzinfo is None:
            last_check_dt = last_check_dt.replace(tzinfo=timezone.utc)
    except ValueError as e:
        return ReviewMonitorResponse(
            status="error",
            error_message=f"Неверный формат last_check_date: {e}. Ожидается ISO 8601."
        )

    collected_reviews: List[ReviewModel] = []
    
    async with Stealth().use_async(async_playwright()) as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='ru-RU',
            timezone_id='Europe/Moscow'
        )
        page = await context.new_page()
        
        try:
            await random_delay(1.0, 2.5)
            logger.info("Открытие страницы...")
            await page.goto(str(request.url), wait_until="domcontentloaded", timeout=30000)
            await random_delay(2.5, 4.5)
            
            # Проверка капчи (по аналогии с основным парсером)
            captcha_selector = ".captcha-container, iframe[src*='showcaptcha'], .CheckboxCaptcha" 
            if await page.locator(captcha_selector).count() > 0:
                logger.warning(f"Обнаружена капча на странице {request.url}")
                return ReviewMonitorResponse(status="captcha", error_message="Обнаружена капча (SmartCaptcha)")

            # --- Переход во вкладку "Отзывы" ---
            # Ищем ссылку или вкладку с текстом "Отзывы" (для Яндекса и 2ГИС)
            logger.info("Переход во вкладку Отзывы...")
            reviews_tab_selectors = [
                "a.tabs-select-view__title:has-text('Отзывы')",
                "div.tabs-select-view__title:has-text('Отзывы')",
                "a:has-text('Отзывы')"
            ]
            tab_clicked = False
            for selector in reviews_tab_selectors:
                elements = await page.locator(selector).all()
                for el in elements:
                    if await el.is_visible():
                        await el.click()
                        tab_clicked = True
                        break
                if tab_clicked:
                    break
            
            if tab_clicked:
                await random_delay(2.0, 4.0)
            else:
                # Возможно, мы уже на странице отзывов или структура другая
                logger.debug("Вкладка 'Отзывы' не найдена или не кликабельна.")

            # --- Сортировка по новизне (примерно для Яндекса) ---
            # Это хрупкий момент, селекторы часто меняются
            sort_button_selector = ".rating-sort-view__button, .business-reviews-sort-view__button, button:has-text('По умолчанию')"
            try:
                sort_btn = page.locator(sort_button_selector).first
                if await sort_btn.is_visible():
                    await sort_btn.click()
                    await random_delay(1.0, 2.0)
                    newest_option = page.locator("div[role='option'], div.menu__item").filter(has_text="По новизне").first
                    if await newest_option.is_visible():
                        await newest_option.click()
                        logger.info("Включена сортировка 'По новизне'")
                        await random_delay(2.0, 3.5)
            except Exception as e:
                logger.warning(f"Не удалось применить сортировку: {e}")

            # --- Парсинг списка отзывов ---
            logger.info("Сбор отзывов...")
            # Селектор карточки отзыва
            review_card_selector = ".business-review-view, .review-card, .comment"
            
            # Для скролла
            scroll_container_selector = ".scroll__container, .business-reviews-list-view, .sidebar-toggle-view"
            
            max_scrolls = 20
            scroll_count = 0
            stop_scraping = False
            processed_review_texts = set()

            while scroll_count < max_scrolls and not stop_scraping:
                reviews = await page.locator(review_card_selector).all()
                
                # Обработка текущих загруженных отзывов
                for review in reviews:
                    try:
                        # Текст
                        text_locator = review.locator(".business-review-view__body-text, .review-text, span.review-snippet-view__text, span.review-snippet-view__body").first
                        if await text_locator.count() > 0:
                            text = await text_locator.inner_text()
                        else:
                            # Фолбэк на поиск любого длинного текста внутри карточки
                            text = ""
                            texts = await review.all_inner_texts()
                            if texts and len(texts[0]) > 20:
                                # Обычно текст отзыва - самый длинный блок
                                text_candidates = sorted(texts[0].split('\n'), key=len, reverse=True)
                                if text_candidates: text = text_candidates[0]
                        
                        if text in processed_review_texts and text != "":
                            continue
                        
                        # Автор
                        author_locator = review.locator(".business-review-view__author, .review-card__author, span[itemprop='name']").first
                        author = await author_locator.inner_text() if await author_locator.count() > 0 else "Аноним"
                        
                        # Чистим автора от лишних переносов строк
                        if author: author = author.split('\n')[0].strip()
                        
                        # Дата
                        date_locator = review.locator(".business-review-view__date, .review-card__date, meta[itemprop='datePublished']").first
                        date_raw = ""
                        if await date_locator.count() > 0:
                            # Сначала проверяем атрибут content (для Яндекса часто в meta)
                            content_attr = await date_locator.get_attribute("content")
                            if content_attr:
                                date_raw = content_attr
                            else:
                                date_raw = await date_locator.inner_text()
                        
                        # Оценка (опционально, бывает скрыта или в звездах)
                        rating_val = None
                        rating_locator = review.locator("meta[itemprop='reviewRating'] meta[itemprop='ratingValue']")
                        if await rating_locator.count() > 0:
                            rating_str = await rating_locator.first.get_attribute("content")
                            if rating_str: rating_val = float(rating_str)
                        else:
                            # Эвристика по количеству закрашенных звезд
                            stars = await review.locator("path[fill*='url'], span[class*='star'], .business-rating-badge-view__star_full").count()
                            if stars > 0:
                                rating_val = float(min(stars, 5))
                        
                        parsed_dt = parse_russian_date(date_raw) if date_raw else None
                        
                        has_reply = False
                        reply_texts = ["официальный ответ", "представитель компании", "ответ владельца", "ответил(а)"]
                        for rt in reply_texts:
                            if await review.locator(f"text=/{rt}/i").count() > 0:
                                has_reply = True
                                break

                        # Проверка даты на остановку (если дата распарсилась)
                        if parsed_dt:
                            if parsed_dt <= last_check_dt:
                                logger.info(f"Достигнут отзыв старше или равный last_check_date ({parsed_dt} <= {last_check_dt}). Остановка.")
                                stop_scraping = True
                                break
                        
                        # Добавляем в результат
                        review_model = ReviewModel(
                            author=author.strip() if author else None,
                            text=text.strip() if text else None,
                            rating=rating_val,
                            date_parsed=parsed_dt.isoformat() if parsed_dt else None,
                            date_raw=date_raw.strip() if date_raw else None,
                            has_reply=has_reply
                        )
                        collected_reviews.append(review_model)
                        if text:
                            processed_review_texts.add(text)
                            
                    except Exception as rev_e:
                        logger.warning(f"Ошибка при парсинге одного из отзывов: {rev_e}")

                if stop_scraping:
                    break

                # Скроллинг
                logger.debug(f"Скроллинг страницы... ({scroll_count + 1}/{max_scrolls})")
                
                # Попробуем скроллить последний элемент отзывов в область видимости
                if len(reviews) > 0:
                    try:
                        await reviews[-1].scroll_into_view_if_needed()
                    except Exception:
                        pass
                        
                # Альтернативный скролл
                await page.mouse.wheel(0, 2000)
                await random_delay(1.5, 3.0)
                scroll_count += 1
                
                # Проверим, не появилось ли новых отзывов
                new_reviews_count = await page.locator(review_card_selector).count()
                if new_reviews_count == len(reviews) and scroll_count > 3:
                    logger.info("Новые отзывы не подгружаются, возможно конец списка.")
                    break

            logger.success(f"Парсинг отзывов завершен. Собрано: {len(collected_reviews)}")
            return ReviewMonitorResponse(
                status="success",
                new_reviews=collected_reviews
            )

        except PlaywrightTimeoutError as e:
            logger.error(f"Таймаут при парсинге {request.url}: {str(e)}")
            return ReviewMonitorResponse(
                status="error",
                error_message="Таймаут ожидания страницы или элементов"
            )
        except Exception as e:
            logger.exception(f"Критическая ошибка при парсинге {request.url}: {str(e)}")
            return ReviewMonitorResponse(
                status="error",
                error_message=str(e)
            )
        finally:
            await random_delay(0.5, 1.5)
            await context.close()
            await browser.close()
