import asyncio
import httpx
from bs4 import BeautifulSoup
from loguru import logger
from urllib.parse import urlparse, quote
from typing import Tuple, Optional
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import json
import re

from app.schemas.scraper import (
    ReputationSearchRequest,
    ReputationSearchResponse,
    ReputationSiteResult
)
from app.services.twogis_parser import random_delay
from app.services.reputation_history_db import save_reputation_search_result, get_reputation_history
from app.services.google_sheets import append_reputation_results_to_sheet
from app.services.site_extractors import try_extract_specific
from ddgs import DDGS

# User-Agent для обхода простых блокировок в httpx
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
}

async def extract_title(url: str) -> str:
    """Извлекает и очищает title с сайта."""
    try:
        async with httpx.AsyncClient(headers=HEADERS, verify=False, timeout=10.0) as client:
            resp = await client.get(url, follow_redirects=True)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')
            title_tag = soup.find('title')
            if not title_tag or not title_tag.string:
                return urlparse(url).netloc
            
            raw_title = title_tag.string.strip()
            
            # Более умная очистка тайтла
            # Убираем типичные SEO-слова, но оставляем бренд
            import re
            spam_words = ["официальный сайт", "недорого", "в Москве", "в Санкт-Петербурге", "в спб", "цены", "купить", "заказать"]
            cleaned_title = raw_title
            for w in spam_words:
                cleaned_title = re.sub(r'(?i)\b' + w + r'\b', '', cleaned_title)
                
            # Заменяем разделители на пробелы
            cleaned_title = cleaned_title.replace('|', ' ').replace('-', ' ').replace('–', ' ').replace('—', ' ')
            
            # Оставляем первые 6 слов для качественного запроса
            words = cleaned_title.split()
            final_title = " ".join(words[:6])
            
            if not final_title:
                return urlparse(url).netloc
                
            return final_title
    except Exception as e:
        logger.error(f"Ошибка при извлечении title с {url}: {e}")
        return urlparse(url).netloc

async def extract_rating_data(html: str, domain: str = "") -> tuple[float | None, int | None]:
    """Ищет AggregateRating в JSON-LD и микроразметке."""
    soup = BeautifulSoup(html, 'html.parser')
    
    # 0. Попытка использовать специфичный парсер для домена
    if domain:
        r_val, c_val = try_extract_specific(domain, soup)
        if r_val is not None or c_val is not None:
            logger.info(f"Сработал специфичный парсер для {domain}: {r_val}, {c_val}")
            return r_val, c_val

    # 1. Поиск в JSON-LD
    for script in soup.find_all('script', type='application/ld+json'):
        if not script.string:
            continue
        try:
            data = json.loads(script.string)
            # Иногда JSON-LD это список объектов
            if not isinstance(data, list):
                data = [data]
            
            for item in data:
                if isinstance(item, dict):
                    # Если AggregateRating на верхнем уровне
                    if item.get('@type') == 'AggregateRating':
                        rating = float(item.get('ratingValue', 0))
                        count = int(item.get('reviewCount', item.get('ratingCount', 0)))
                        return rating, count
                    
                    # Если AggregateRating внутри Organization / LocalBusiness
                    agg = item.get('aggregateRating')
                    if isinstance(agg, dict) and agg.get('@type') == 'AggregateRating':
                        rating = float(agg.get('ratingValue', 0))
                        count = int(agg.get('reviewCount', agg.get('ratingCount', 0)))
                        return rating, count
        except Exception:
            continue
            
    # 2. Поиск в микроразметке (Microdata)
    rating_val = None
    count_val = None
    
    agg_rating = soup.find(itemprop='aggregateRating')
    if agg_rating:
        rating_tag = agg_rating.find(itemprop='ratingValue')
        count_tag = agg_rating.find(itemprop='reviewCount') or agg_rating.find(itemprop='ratingCount')
    else:
        rating_tag = soup.find(itemprop='ratingValue')
        count_tag = soup.find(itemprop='reviewCount') or soup.find(itemprop='ratingCount')
        
    if rating_tag:
        try:
            val = rating_tag.get('content') or rating_tag.text
            rating_val = float(val.replace(',', '.').strip())
        except Exception:
            pass
            
    if count_tag:
        try:
            val = count_tag.get('content') or count_tag.text
            count_val = int(''.join(filter(str.isdigit, val)))
        except Exception:
            pass
            
    if rating_val is not None:
        if rating_val > 10:
            rating_val = round(rating_val / 20, 1) # например, 32 из 100 -> 1.6 из 5
        elif rating_val > 5:
            rating_val = round(rating_val / 2, 1) # например, 8 из 10 -> 4.0 из 5
        return rating_val, count_val
        
    # 3. Кастомные селекторы для проблемных сайтов (2GIS, Zoon и т.д.)
    # 2GIS
    twogis_rating = soup.select_one('div[class*="_rating"] span, div[class*="rating"] span')
    twogis_count = soup.select_one('div[class*="_reviews"] span, div[class*="reviews"] span')
    # Ищем в тексте "рейтинг X" или "X отзывов" как запасной вариант (Zoon / 2GIS)
    text_content = soup.get_text(separator=' ', strip=True).lower()
    import re
    if rating_val is None:
        # Zoon rating is often in a specific badge
        zoon_rating = soup.select_one('.rating-value, .rating span, .stars-rating__value')
        if zoon_rating:
            try:
                rating_val = float(zoon_rating.text.replace(',', '.').strip())
            except: pass
            
    if count_val is None:
        # Попробуем найти количество отзывов в тексте ссылок
        for a in soup.find_all('a'):
            if 'отзыв' in a.text.lower():
                nums = re.findall(r'\d+', a.text)
                if nums:
                    count_val = int(nums[0])
                    break
                    
    if rating_val is None or count_val is None:
        # Универсальная регулярка для 2GIS и прочих сайтов: "4.7 45 оценок"
        m_general = re.search(r'(\d[\.,]\d)\s*(?:/\s*5)?\s*(\d+)\s*(?:оцен|отзыв)', text_content)
        if m_general:
            if rating_val is None:
                rating_val = float(m_general.group(1).replace(',', '.'))
            if count_val is None:
                count_val = int(m_general.group(2))
                
    if rating_val is not None:
        if rating_val > 10:
            rating_val = round(rating_val / 20, 1)
        elif rating_val > 5:
            rating_val = round(rating_val / 2, 1)

    return rating_val, count_val

def calculate_relevance_score(request: ReputationSearchRequest, title: str, h1: str, text: str) -> int:
    score = 0
    title_lower = (title or "").lower()
    h1_lower = (h1 or "").lower()
    text_lower = (text or "").lower()
    
    company_lower = request.company.lower()
    city_lower = request.city.lower()
    
    # 1. Company match
    if company_lower in title_lower or company_lower in h1_lower:
        score += 50
    elif company_lower in text_lower:
        score += 30
        
    # 2. City match
    if city_lower in title_lower or city_lower in h1_lower:
        score += 30
    elif city_lower in text_lower:
        score += 20
        
    # 3. Address match
    if request.address:
        addr_words = [w for w in request.address.lower().split() if len(w) > 3]
        for w in addr_words:
            if w in text_lower:
                score += 15
                break
                
    # 4. Direction match
    direction_lower = request.direction.lower()
    if direction_lower in title_lower or direction_lower in h1_lower:
        score += 20
    elif direction_lower in text_lower:
        score += 10
        
    # 5. Website match
    if request.website:
        domain = urlparse(request.website).netloc.replace('www.', '')
        if not domain:
            domain = request.website.replace('www.', '').replace('http://', '').replace('https://', '').split('/')[0]
        if domain.lower() in text_lower or domain.lower() in title_lower or domain.lower() in h1_lower:
            score += 20
            
    return score

async def parse_aggregator_site(url: str, context, request: ReputationSearchRequest, previous_site_data: dict = None) -> ReputationSiteResult:
    """Парсит страницу агрегатора и извлекает рейтинг с помощью Playwright."""
    domain = urlparse(url).netloc.replace('www.', '')
    page = None
    try:
        page = await context.new_page()
        # Ставим таймаут поменьше, чтобы не висеть долго на тяжелых сайтах
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        
        # Ждем немного для отработки JS и анти-бот сервисов (ServicePipe / Cloudflare)
        await asyncio.sleep(4)
        
        try:
            html = await page.content()
        except Exception:
            # Если страница еще навигируется (napopravku), подождем еще и попробуем
            await asyncio.sleep(2)
            html = await page.content()
            
        rating, count = await extract_rating_data(html, domain)
            
        # Оценка релевантности
        try:
            soup = BeautifulSoup(html, 'html.parser')
            page_title = soup.title.string if soup.title else ""
            h1_tag = soup.find('h1')
            h1_text = h1_tag.get_text(separator=' ', strip=True) if h1_tag else ""
            body_tag = soup.find('body')
            page_text = body_tag.get_text(separator=' ', strip=True)[:3000] if body_tag else ""
            
            score = calculate_relevance_score(request, page_title, h1_text, page_text)
            logger.info(f"Оценка релевантности для {domain}: {score} баллов")
            
            if score < 30:
                return ReputationSiteResult(
                    url=url, 
                    domain=domain,
                    rating=rating,
                    reviews_count=count,
                    status=f"irrelevant (score: {score})"
                )
        except Exception as e:
            logger.debug(f"Ошибка при извлечении метаданных для скоринга: {e}")
            
        prev_rating = None
        prev_count = None
        rating_change = None
        count_change = None
        
        if previous_site_data:
            prev_r_raw = previous_site_data.get("rating")
            prev_c_raw = previous_site_data.get("reviews_count")
            
            try:
                prev_rating = float(prev_r_raw) if prev_r_raw and prev_r_raw != "-" else None
            except:
                prev_rating = None
                
            try:
                prev_count = int(str(prev_c_raw).replace(" ", "")) if prev_c_raw and prev_c_raw != "-" else None
            except:
                prev_count = None
            
            if rating is not None and prev_rating is not None:
                rating_change = round(rating - prev_rating, 2)
            if count is not None and prev_count is not None:
                count_change = count - prev_count

        has_changes = True
        screenshot_url = None
        
        if previous_site_data:
            same_rating = (rating == prev_rating)
            same_count = (count == prev_count)
            if same_rating and same_count:
                has_changes = False
                screenshot_url = previous_site_data.get("screenshot_url")
                
        if has_changes:
            import uuid
            import os
            try:
                screenshot_filename = f"{uuid.uuid4()}.png"
                screenshot_dir = os.path.join("app", "static", "screenshots")
                os.makedirs(screenshot_dir, exist_ok=True)
                screenshot_path = os.path.join(screenshot_dir, screenshot_filename)
                # Делаем скриншот на всю высоту или видимую часть
                await page.screenshot(path=screenshot_path)
                screenshot_url = f"https://review.profi-sozinov.ru/static/screenshots/{screenshot_filename}"
            except Exception as e:
                logger.error(f"Ошибка при создании скриншота: {e}")
        
        return ReputationSiteResult(
            url=url,
            domain=domain,
            rating=rating,
            reviews_count=count,
            previous_rating=prev_rating,
            previous_reviews_count=prev_count,
            rating_change=rating_change,
            reviews_count_change=count_change,
            screenshot_url=screenshot_url,
            status="success" if rating is not None else "no_rating_found"
        )
    except Exception as e:
        return ReputationSiteResult(url=url, domain=domain, status=f"error ({str(e)[:50]})")
    finally:
        if page:
            await page.close()

async def search_reputation(request: ReputationSearchRequest):
    parts = []
    if request.direction: parts.append(request.direction)
    parts.append(request.company)
    if request.city: parts.append(request.city)
    parts.append("отзывы")
    
    search_query = " ".join(parts)
    logger.info(f"Сформирован запрос: '{search_query}'")
    yield {"type": "progress", "message": f"Сформирован поисковой запрос: '{search_query}'"}
    
    # Получаем предыдущую историю для этой компании
    history = get_reputation_history(request.company)
    last_search_result = history[0] if history else None
    
    previous_sites = {}
    if last_search_result and "result" in last_search_result and "sites" in last_search_result["result"]:
        for site in last_search_result["result"]["sites"]:
            previous_sites[site.get("domain")] = site
    
    # 2. Ищем сайты через DuckDuckGo (без браузера и капчи)
    links = []
    seen_domains = set()
    
    yield {"type": "progress", "message": "Ищем сайты-отзовики..."}
    try:
        loop = asyncio.get_event_loop()
        def _do_search():
            with DDGS() as ddgs:
                return [r for r in ddgs.text(search_query, max_results=30)]
                
        results = await loop.run_in_executor(None, _do_search)
        
        for r in results:
            href = r.get('href', '')
            if href.startswith('http'):
                domain = urlparse(href).netloc.replace('www.', '')
                if domain not in seen_domains:
                    seen_domains.add(domain)
                    links.append(href)
                    
        if len(links) == 0:
            yield {"type": "result", "data": ReputationSearchResponse(
                status="error",
                website_title=request.company,
                search_query=search_query,
                error_message="Поисковик не вернул результатов для этого запроса."
            ).dict()}
            return
            
    except Exception as e:
        logger.error(f"Ошибка при поиске через DDGS: {e}")
        yield {"type": "result", "data": ReputationSearchResponse(
            status="error",
            website_title=request.company,
            search_query=search_query,
            error_message=f"Ошибка поиска: {e}"
        ).dict()}
        return
        
    links = links[:30] # Ограничиваем до 30
    yield {"type": "progress", "message": f"Найдено {len(links)} сайтов-агрегаторов. Начинаем сбор оценок..."}
    logger.info(f"Найдено {len(links)} сайтов-агрегаторов. Начинаем сбор оценок...")
    
    results = []
    # 3. Асинхронно парсим найденные сайты батчами через Playwright
    try:
        async with Stealth().use_async(async_playwright()) as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            
            batch_size = 5
            total_batches = (len(links) + batch_size - 1) // batch_size
            for i in range(0, len(links), batch_size):
                batch_num = i // batch_size + 1
                batch = links[i:i+batch_size]
                yield {"type": "progress", "message": f"Обработка сайтов (пачка {batch_num} из {total_batches})..."}
                tasks = [parse_aggregator_site(url, context, request, previous_sites.get(urlparse(url).netloc.replace('www.', ''))) for url in batch]
                batch_results = await asyncio.gather(*tasks)
                results.extend(batch_results)
                
            await browser.close()
    except Exception as e:
        logger.error(f"Ошибка при парсинге агрегаторов: {e}")
        logger.error(f"Ошибка при сборе рейтингов: {e}")
        # Заполняем оставшиеся ссылки ошибками
        for url in links[len(results):]:
            domain = urlparse(url).netloc.replace('www.', '')
            results.append(ReputationSiteResult(url=url, domain=domain, status=f"error (batch fail)"))
    
    response_data = ReputationSearchResponse(
        status="success",
        website_title=request.company,
        search_query=search_query,
        sites=results
    ).dict()
    
    # Сохраняем в локальную БД
    try:
        saved_entry = save_reputation_search_result(request.company, search_query, response_data)
        response_data['history_id'] = saved_entry['id']
    except Exception as e:
        logger.error(f"Ошибка при сохранении истории в БД: {e}")
        
    # Сохраняем в Google Таблицу
    try:
        # Для того чтобы не блокировать event loop, запускаем в executor
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, 
            append_reputation_results_to_sheet, 
            request.company, 
            search_query, 
            response_data
        )
    except Exception as e:
        logger.error(f"Ошибка при сохранении в Google Таблицы: {e}")

    yield {"type": "result", "data": response_data}
