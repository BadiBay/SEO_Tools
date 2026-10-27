import asyncio
import random
from typing import List, Optional
from loguru import logger
from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeoutError
from playwright_stealth import Stealth

from app.schemas.scraper import (
    CompetitorAnalysisRequest, CompetitorAnalysisResponse, 
    CompetitorModel, CompetitorReview
)


async def random_delay(min_seconds: float = 1.0, max_seconds: float = 3.0) -> None:
    delay = random.uniform(min_seconds, max_seconds)
    logger.debug(f"Ожидание {delay:.2f} сек...")
    await asyncio.sleep(delay)


async def search_competitors_urls(page: Page, request: CompetitorAnalysisRequest) -> List[tuple[str, bool]]:
    """
    Поиск конкурентов на Яндекс Картах по координатам и запросу.
    Возвращает список URL карточек конкурентов.
    (В будущем эту функцию можно заменить на вызов Yandex Search API)
    """
    logger.info(f"Поиск конкурентов по запросу '{request.query}' около {request.lat}, {request.lon}...")
    
    # Приблизительный расчет spn (размаха карты) по радиусу (1 градус ~ 111 км)
    spn_val = request.radius / 111000.0
    search_url = f"https://yandex.ru/maps/?ll={request.lon}%2C{request.lat}&spn={spn_val}%2C{spn_val}&text={request.query}"
    
    await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
    await random_delay(3.0, 5.0)

    # Ищем ссылки на карточки организаций
    link_selector = "a.search-snippet-view__link-overlay, a.link-overlay"
    
    # Ждем появления хотя бы одного результата
    try:
        await page.wait_for_selector(link_selector, timeout=10000)
    except PlaywrightTimeoutError:
        logger.warning("Не удалось найти результаты поиска конкурентов.")
        return []

    elements = await page.locator("li.search-snippet-view, li[class*='snippet']").all()
    results = []
    
    for el in elements:
        # Пытаемся найти ссылку внутри сниппета
        link_loc = el.locator("a.search-snippet-view__link-overlay, a.link-overlay").first
        if await link_loc.count() == 0:
            continue
            
        href = await link_loc.get_attribute("href")
        if not href or "/org/" not in href:
            continue
            
        full_url = href if href.startswith("http") else f"https://yandex.ru{href}"
        clean_url = full_url.split("?")[0]
        
        # Определяем рекламу по списку сниппетов (в Яндексе они часто помечены)
        is_ad = False
        class_attr = await el.get_attribute("class") or ""
        if "advert" in class_attr.lower() or "priority" in class_attr.lower():
            is_ad = True
            
        if not is_ad:
            # Ищем бейджик "Реклама" внутри сниппета
            ad_text = await el.evaluate('''node => {
                return Array.from(node.querySelectorAll('span, div')).some(e => e.innerText === 'Реклама');
            }''')
            if ad_text:
                is_ad = True
                
        # Если ссылка уникальная, добавляем
        if not any(r[0] == clean_url for r in results):
            results.append((clean_url, is_ad))
            
        if len(results) >= request.limit:
            break
            
    logger.info(f"Найдено конкурентов: {len(results)}")
    return results


async def parse_competitor_card(page: Page, url: str, is_ad_from_search: bool = False) -> Optional[CompetitorModel]:
    """
    Сбор данных из карточки одного конкурента.
    """
    logger.info(f"Сбор данных конкурента: {url}")
    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    await random_delay(2.0, 4.0)
    
    # 1. Парсинг названия
    name_selector = "h1.orgpage-header-view__header, h1.business-card-title-view"
    name = "Неизвестно"
    try:
        name_locator = page.locator(name_selector).first
        if await name_locator.count() > 0:
            name = await name_locator.inner_text()
    except Exception:
        pass

    # 2. Детекция платного размещения (Ad Detection)
    # Если is_ad_from_search=True, то мы уже знаем, что это реклама из списка поиска.
    # Дополнительно проверим наличие премиум-витрины на самой карточке.
    is_ad = is_ad_from_search
    ad_type = "premium_placement" if is_ad else None
    
    promo_selectors = [
        ".business-card-premium-view",
        ".business-card-priority-view",
        ".business-showcase-view",
        ".orgpage-showcase-view",
        "div[class*='business-card-promo']",
        "div[class*='showcase']"
    ]
    for selector in promo_selectors:
        try:
            if await page.locator(selector).count() > 0:
                logger.info(f"Найден премиум-блок: {selector}")
                is_ad = True
                ad_type = "premium_block"
                break
        except Exception:
            pass

    # 3. Парсинг рейтинга и количества оценок
    rating_val = None
    reviews_count = None
    
    try:
        rating_locator = page.locator(".business-rating-badge-view__rating-text, .business-header-rating-view__text").first
        if await rating_locator.count() > 0:
            r_text = await rating_locator.inner_text()
            rating_val = float(r_text.replace(',', '.').strip())
            
        reviews_locator = page.locator(".business-rating-amount-view, .business-header-rating-view__text").first
        if await reviews_locator.count() > 0:
            rv_text = await reviews_locator.inner_text()
            digits = ''.join(filter(str.isdigit, rv_text))
            if digits:
                reviews_count = int(digits)
    except Exception as e:
        logger.warning(f"Не удалось извлечь рейтинг/оценки: {e}")

    # 4. Переход в отзывы
    tab_clicked = False
    for selector in ["a.tabs-select-view__title:has-text('Отзывы')", "div.tabs-select-view__title:has-text('Отзывы')"]:
        tab = page.locator(selector).first
        if await tab.count() > 0 and await tab.is_visible():
            await tab.click()
            tab_clicked = True
            break
            
    if not tab_clicked:
        logger.debug("Вкладка Отзывы не найдена.")
        return CompetitorModel(
            name=name, url=url, rating=rating_val, reviews_count=reviews_count, is_ad=is_ad, ad_type=ad_type
        )
        
    await random_delay(2.0, 3.0)
    
    # 5. Собираем отзывы
    positive_reviews: List[CompetitorReview] = []
    negative_reviews: List[CompetitorReview] = []
    
    review_selector = ".business-review-view, .review-snippet-view, article[class*='review']"
    max_scrolls = 5
    scrolls = 0
    processed_count = 0
    
    while scrolls < max_scrolls and (len(positive_reviews) < 5 or len(negative_reviews) < 5):
        reviews = await page.locator(review_selector).all()
        
        for rev in reviews[processed_count:]:
            try:
                # Текст
                text = ""
                text_loc = rev.locator("span.business-review-view__body-text, span.review-snippet-view__text, span[itemprop='reviewBody'], div[itemprop='reviewBody'], .business-review-view__text, .business-review-view__body").first
                if await text_loc.count() > 0:
                    text = await text_loc.inner_text()
                else:
                    # Фолбэк: берем все тексты внутри отзыва по отдельности и находим самую длинную строчку
                    texts_data = await rev.evaluate('''el => {
                        return Array.from(el.querySelectorAll('span, p, div'))
                                    .map(e => e.innerText)
                                    .filter(t => t && t.length > 30);
                    }''')
                    if texts_data:
                        text = max(texts_data, key=len)
                    else:
                        continue # Пропускаем, если не смогли найти нормальный текст
                    
                if not text or len(text) < 10:
                    continue

                # Оценка (пытаемся найти явную)
                rev_rating = 0.0
                rating_loc = rev.locator("meta[itemprop='ratingValue']")
                if await rating_loc.count() > 0:
                    r_str = await rating_loc.first.get_attribute("content")
                    if r_str: rev_rating = float(r_str)
                else:
                    # Эвристика по количеству звезд (пути SVG с закрашенным цветом)
                    stars = await rev.locator("path[fill*='url'], span[class*='star']").count()
                    if stars > 0:
                        rev_rating = float(min(stars, 5))
                    else:
                        # Анализ тональности по оценке текста или просто относим в нейтральные
                        text_lower = text.lower()
                        if any(w in text_lower for w in ['ужасно', 'плохо', 'отвратительно', 'не советую']):
                            rev_rating = 1.0
                        elif any(w in text_lower for w in ['отлично', 'хорошо', 'супер', 'спасибо']):
                            rev_rating = 5.0
                        else:
                            continue # Пропускаем, если не можем определить оценку
                    
                # Проверка на наличие ответа
                has_reply = False
                reply_texts = ["официальный ответ", "представитель компании", "ответ владельца", "ответил(а)"]
                for rt in reply_texts:
                    if await rev.locator(f"text=/{rt}/i").count() > 0:
                        has_reply = True
                        break

                # Классификация
                rev_type = "positive" if rev_rating >= 4 else ("negative" if rev_rating <= 3 else "neutral")
                
                # Проверка на уникальность
                clean_text = text.strip()[:200] + "..." # Берем начало для сравнения
                
                if rev_type == "positive" and len(positive_reviews) < 5:
                    if not any(r.text.startswith(clean_text[:50]) for r in positive_reviews):
                        positive_reviews.append(CompetitorReview(text=clean_text, rating=rev_rating, type=rev_type, has_reply=has_reply))
                        
                elif rev_type == "negative" and len(negative_reviews) < 5:
                    if not any(r.text.startswith(clean_text[:50]) for r in negative_reviews):
                        negative_reviews.append(CompetitorReview(text=clean_text, rating=rev_rating, type=rev_type, has_reply=has_reply))
                        
            except Exception as e:
                logger.debug(f"Ошибка парсинга одного отзыва: {e}")
                continue
                
        processed_count = len(reviews)
        
        if len(positive_reviews) >= 5 and len(negative_reviews) >= 5:
            break
            
        # Скролл
        await page.mouse.wheel(0, 2000)
        await random_delay(1.5, 2.5)
        scrolls += 1
        
    return CompetitorModel(
        name=name,
        url=url,
        rating=rating_val,
        reviews_count=reviews_count,
        is_ad=is_ad,
        ad_type=ad_type,
        top_positive_reviews=positive_reviews,
        top_negative_reviews=negative_reviews
    )


async def parse_competitors_analysis(request: CompetitorAnalysisRequest) -> CompetitorAnalysisResponse:
    logger.info(f"Начало конкурентного анализа...")
    
    competitors_list: List[CompetitorModel] = []
    
    async with Stealth().use_async(async_playwright()) as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            locale='ru-RU',
            timezone_id='Europe/Moscow'
        )
        page = await context.new_page()
        
        try:
            # Если передана ссылка, нужно извлечь из неё координаты
            if request.url:
                logger.info(f"Определение координат по ссылке: {request.url}")
                await page.goto(request.url, wait_until="domcontentloaded", timeout=30000)
                await random_delay(2.0, 4.0)
                current_url = page.url
                
                # Ищем координаты в URL (Яндекс Карты обычно имеют параметр ll=lon,lat)
                import re
                match = re.search(r'll=([\d.]+)(?:%2C|,)([\d.]+)', current_url)
                if match:
                    request.lon = float(match.group(1))
                    request.lat = float(match.group(2))
                    logger.info(f"Координаты определены: lat={request.lat}, lon={request.lon}")
                else:
                    return CompetitorAnalysisResponse(
                        status="error",
                        error_message="Не удалось определить координаты из ссылки."
                    )
            elif not request.lat or not request.lon:
                return CompetitorAnalysisResponse(
                    status="error",
                    error_message="Необходимо указать ссылку или координаты."
                )

            # 1. Поиск URL конкурентов
            urls = await search_competitors_urls(page, request)
            if not urls:
                return CompetitorAnalysisResponse(
                    status="error",
                    error_message="Не найдено ни одного конкурента по заданному запросу и координатам."
                )
                
            # 2. Сбор данных по каждому конкуренту
            for url, is_ad_from_search in urls:
                try:
                    comp_model = await parse_competitor_card(page, url, is_ad_from_search)
                    if comp_model:
                        competitors_list.append(comp_model)
                except Exception as e:
                    logger.warning(f"Ошибка парсинга конкурента {url}: {e}")
                    
            logger.success(f"Анализ завершен. Собрано {len(competitors_list)} конкурентов.")
            return CompetitorAnalysisResponse(
                status="success",
                competitors=competitors_list
            )
            
        except PlaywrightTimeoutError as e:
            return CompetitorAnalysisResponse(status="error", error_message=f"Таймаут: {str(e)}")
        except Exception as e:
            return CompetitorAnalysisResponse(status="error", error_message=str(e))
        finally:
            await context.close()
            await browser.close()
