import asyncio
import random
from datetime import datetime, timezone
from typing import Optional, List
import dateparser
from loguru import logger
from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeoutError
from playwright_stealth import Stealth

from app.schemas.scraper import (
    YandexMapCardRequest, YandexMapCardResponse,
    ReviewMonitorRequest, ReviewMonitorResponse, ReviewModel,
    CompetitorAnalysisRequest, CompetitorAnalysisResponse,
    CompetitorModel, CompetitorReview
)

async def random_delay(min_seconds: float = 1.0, max_seconds: float = 3.0) -> None:
    delay = random.uniform(min_seconds, max_seconds)
    logger.debug(f"Ожидание {delay:.2f} сек...")
    await asyncio.sleep(delay)

def parse_russian_date(date_str: str) -> Optional[datetime]:
    try:
        dt = dateparser.parse(
            date_str,
            languages=['ru'],
            settings={'TIMEZONE': 'UTC', 'RETURN_AS_TIMEZONE_AWARE': True}
        )
        return dt
    except Exception:
        return None

# --- MODULE 1: Basic Parsing ---

async def parse_twogis_map_card(request: YandexMapCardRequest) -> YandexMapCardResponse:
    logger.info(f"Начало парсинга 2GIS карточки: {request.url}")
    
    async with Stealth().use_async(async_playwright()) as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        try:
            await page.goto(str(request.url), wait_until="domcontentloaded", timeout=30000)
            await random_delay(2.0, 4.0)
            
            # Обход страницы обновления браузера
            try:
                accept_btn = page.locator('#acceptRiskButton')
                if await accept_btn.count() > 0:
                    await accept_btn.click()
                    await page.wait_for_load_state('domcontentloaded')
                    await random_delay(2.0, 4.0)
            except: pass
            
            # Проверка на капчу 2ГИС
            body_text = await page.evaluate("document.body.innerText")
            if "подозрительную активность с вашего IP" in body_text:
                return YandexMapCardResponse(status="error", error_message="2GIS заблокировал доступ (CAPTCHA). Требуется смена IP или использование прокси.")
            
            # Эвристика: ищем текст с рейтингом и оценками        
            rating_val = None
            reviews_count = None
            
            # В 2GIS рейтинг обычно выглядит как "4.5" или "4,5", а оценки "120 оценок"
            # Соберем все текстовые узлы карточки
            all_texts = await page.evaluate('''() => {
                const els = Array.from(document.querySelectorAll('*'));
                return els.filter(el => el.children.length === 0 && el.textContent.trim().length > 0)
                          .map(el => el.textContent.trim());
            }''')
            
            for text in all_texts:
                text_lower = text.lower()
                # Поиск оценок
                if 'оценк' in text_lower or 'отзыв' in text_lower:
                    digits = ''.join(filter(str.isdigit, text))
                    if digits and len(digits) < 10 and not reviews_count:
                        try:
                            reviews_count = int(digits)
                        except ValueError:
                            pass
                        
                # Поиск рейтинга (например "4.8")
                if len(text) <= 4 and text[0].isdigit() and ('.' in text or ',' in text):
                    try:
                        val = float(text.replace(',', '.'))
                        if 1.0 <= val <= 5.0 and not rating_val:
                            rating_val = val
                    except:
                        pass

            if rating_val is None and reviews_count is None:
                return YandexMapCardResponse(
                    status="error",
                    error_message="Не удалось найти рейтинг и количество оценок на странице 2GIS."
                )
                
            return YandexMapCardResponse(
                status="success",
                rating=rating_val,
                reviews_count=reviews_count
            )
            
        except Exception as e:
            logger.exception(f"Ошибка 2GIS парсинга: {e}")
            return YandexMapCardResponse(status="error", error_message=str(e))
        finally:
            await context.close()
            await browser.close()


# --- MODULE 2: Reviews Monitor ---

async def parse_twogis_reviews_monitor(request: ReviewMonitorRequest) -> ReviewMonitorResponse:
    logger.info(f"Мониторинг 2GIS отзывов: {request.url}")
    
    try:
        last_check_dt = datetime.fromisoformat(request.last_check_date.replace("Z", "+00:00"))
        if last_check_dt.tzinfo is None:
            last_check_dt = last_check_dt.replace(tzinfo=timezone.utc)
    except ValueError as e:
        return ReviewMonitorResponse(status="error", error_message=f"Неверный формат даты: {e}")

    collected_reviews: List[ReviewModel] = []
    
    async with Stealth().use_async(async_playwright()) as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        try:
            await page.goto(str(request.url), wait_until="domcontentloaded", timeout=30000)
            await random_delay(3.0, 5.0)
            
            # Обход страницы обновления браузера
            try:
                accept_btn = page.locator('#acceptRiskButton')
                if await accept_btn.count() > 0:
                    await accept_btn.click()
                    await page.wait_for_load_state('domcontentloaded')
                    await random_delay(2.0, 4.0)
            except: pass
            
            # Проверка на капчу 2ГИС
            body_text = await page.evaluate("document.body.innerText")
            if "подозрительную активность с вашего IP" in body_text:
                return ReviewMonitorResponse(status="error", error_message="2GIS заблокировал доступ (CAPTCHA). Требуется смена IP или использование прокси.")
                
            # Переход на вкладку Отзывы
            current_url = page.url
            if '/firm/' in current_url and '/tab/reviews' not in current_url:
                base_url = current_url.split('?')[0]
                reviews_url = base_url + '/tab/reviews'
                await page.goto(reviews_url, wait_until="domcontentloaded", timeout=30000)
                await random_delay(3.0, 5.0)
            
            # Эвристика парсинга контейнеров с отзывами
            # Ищем блоки, содержащие длинный текст и дату
            max_scrolls = 15
            scroll_count = 0
            stop_scraping = False
            processed_texts = set()
            
            while scroll_count < max_scrolls and not stop_scraping:
                # В 2GIS отзывы обычно в больших div'ах. Ищем div, у которых есть дата и текст
                # Простейшая стратегия: берем все тексты на странице и объединяем их логически
                # Так как классы рандомные, мы не можем использовать конкретные классы.
                
                # Ищем блоки отзывов через анализ всего текста страницы
                body_text = await page.evaluate("document.body.innerText")
                lines = [line.strip() for line in body_text.split('\n') if line.strip()]
                
                import re
                date_pattern = re.compile(r'^(вчера|сегодня|\d{1,2}\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)(\s+\d{4})?)(,\s*официальный ответ)?$', re.IGNORECASE)
                
                for i, line in enumerate(lines):
                    if len(line) > 35:
                        continue
                        
                    # Строгая проверка формата даты, чтобы не цеплять "Акция до 4 июля" или "Обновлено 13 июля"
                    if not date_pattern.match(line.strip()):
                        continue
                        
                    parsed_dt = parse_russian_date(line)
                    if not parsed_dt:
                        continue
                        
                    date_str = line
                    
                    author = "Аноним"
                    if i > 0:
                        author = lines[i-1]
                        if "отзыв" in author.lower() and i > 1:
                            author = lines[i-2]
                            
                    text_parts = []
                    next_date_idx = len(lines)
                    for j in range(i+1, len(lines)):
                        if len(lines[j]) < 35 and date_pattern.match(lines[j].strip()) and parse_russian_date(lines[j]):
                            next_date_idx = j
                            break
                            
                    end_idx = next_date_idx
                    if next_date_idx < len(lines):
                        end_idx = next_date_idx - 1
                        if "отзыв" in lines[next_date_idx - 1].lower() and next_date_idx - 2 > i:
                            end_idx = next_date_idx - 2
                            
                    for j in range(i+1, end_idx):
                        l = lines[j]
                        if l in ["Полезно?", "Пожаловаться", "Ответить", "Читать целиком", "Оцените и оставьте отзыв"]:
                            continue
                        if "официальный ответ" in l.lower():
                            break
                        text_parts.append(l)
                        
                    text = " ".join(text_parts).strip()
                    
                    if not text:
                        continue
                        
                    unique_key = f"{author}_{date_str}_{text[:20]}"
                    if unique_key in processed_texts:
                        continue
                        
                    if parsed_dt <= last_check_dt:
                        stop_scraping = True
                        break
                        
                    review_model = ReviewModel(
                        author=author,
                        text=text,
                        rating=5.0, # fallback
                        date_parsed=parsed_dt.isoformat(),
                        date_raw=date_str
                    )
                    collected_reviews.append(review_model)
                    processed_texts.add(unique_key)
                    
                if stop_scraping: break
                
                await page.mouse.wheel(0, 2000)
                await random_delay(1.5, 3.0)
                scroll_count += 1

            return ReviewMonitorResponse(status="success", new_reviews=collected_reviews)
            
        except Exception as e:
            logger.exception(f"Ошибка 2GIS мониторинга: {e}")
            return ReviewMonitorResponse(status="error", error_message=str(e))
        finally:
            await context.close()
            await browser.close()


# --- MODULE 3: Competitors Analysis ---

async def parse_twogis_competitors(request: CompetitorAnalysisRequest) -> CompetitorAnalysisResponse:
    logger.info(f"2GIS поиск конкурентов: '{request.query}' около {request.lat}, {request.lon}")
    
    competitors_list: List[CompetitorModel] = []
    
    async with Stealth().use_async(async_playwright()) as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        try:
            # Если передана ссылка, извлекаем координаты
            if request.url:
                logger.info(f"Определение координат по ссылке 2GIS: {request.url}")
                await page.goto(request.url, wait_until="domcontentloaded", timeout=30000)
                await random_delay(2.0, 4.0)
                
                # Обход страницы обновления браузера
                try:
                    accept_btn = page.locator('#acceptRiskButton')
                    if await accept_btn.count() > 0:
                        await accept_btn.click()
                        await page.wait_for_load_state('domcontentloaded')
                        await random_delay(2.0, 4.0)
                except: pass
                current_url = page.url
                
                # 2GIS URL format can be ?m=37.6173%2C55.7558%2F16
                # or have it inside the path somehow
                import re
                match = re.search(r'm=([\d.]+)(?:%2C|,)([\d.]+)', current_url)
                if match:
                    request.lon = float(match.group(1))
                    request.lat = float(match.group(2))
                    logger.info(f"Координаты 2GIS определены: lat={request.lat}, lon={request.lon}")
                else:
                    # Попробуем вытащить координаты из других элементов, если в URL нет (хотя обычно есть)
                    return CompetitorAnalysisResponse(
                        status="error",
                        error_message="Не удалось определить координаты из ссылки 2GIS."
                    )
            elif not request.lat or not request.lon:
                return CompetitorAnalysisResponse(
                    status="error",
                    error_message="Необходимо указать ссылку или координаты."
                )

            # Поиск по координатам (структура URL 2GIS)
            search_url = f"https://2gis.ru/search/{request.query}/center/{request.lon},{request.lat}/zoom/15"
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await random_delay(4.0, 6.0)
            
            # Обход страницы обновления браузера
            try:
                accept_btn = page.locator('#acceptRiskButton')
                if await accept_btn.count() > 0:
                    await accept_btn.click()
                    await page.wait_for_load_state('domcontentloaded')
                    await random_delay(2.0, 4.0)
            except: pass
            
            # Проверка на капчу 2ГИС
            body_text = await page.evaluate("document.body.innerText")
            if "подозрительную активность с вашего IP" in body_text:
                return CompetitorAnalysisResponse(status="error", error_message="2GIS заблокировал доступ (CAPTCHA). Требуется смена IP или использование прокси.")
            
            # Извлекаем ссылки на фирмы из списка
            # В 2GIS ссылки на фирмы содержат /firm/
            urls = []
            elements = await page.locator("a[href*='/firm/']").all()
            for el in elements:
                href = await el.get_attribute("href")
                if href:
                    full_url = f"https://2gis.ru{href}" if href.startswith("/") else href
                    clean_url = full_url.split("?")[0]
                    if clean_url not in urls:
                        urls.append(clean_url)
                if len(urls) >= request.limit:
                    break
                    
            if not urls:
                return CompetitorAnalysisResponse(status="error", error_message="Конкуренты не найдены.")
                
            # Парсинг каждого конкурента
            for url in urls:
                logger.info(f"Сбор конкурента: {url}")
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await random_delay(2.0, 4.0)
                
                # Тексты
                texts = await page.evaluate('''() => Array.from(document.querySelectorAll('h1, h2, div')).map(e => e.innerText)''')
                name = texts[0] if texts else "Неизвестно"
                
                rating_val = None
                reviews_count = None
                is_ad = False
                ad_type = None
                
                # Простая эвристика для рекламы (в 2GIS рекламные блоки часто имеют 'Реклама' в тексте)
                for txt in texts:
                    if txt and "Реклама" in txt[:20]:
                        is_ad = True
                        ad_type = "premium_block"
                        break
                        
                comp = CompetitorModel(
                    name=name.split('\n')[0][:50],
                    url=url,
                    rating=rating_val,
                    reviews_count=reviews_count,
                    is_ad=is_ad,
                    ad_type=ad_type,
                    top_positive_reviews=[],
                    top_negative_reviews=[]
                )
                competitors_list.append(comp)

            return CompetitorAnalysisResponse(status="success", competitors=competitors_list)
            
        except Exception as e:
            logger.exception(f"Ошибка 2GIS конкурентов: {e}")
            return CompetitorAnalysisResponse(status="error", error_message=str(e))
        finally:
            await context.close()
            await browser.close()
