import asyncio
import httpx
from bs4 import BeautifulSoup
from loguru import logger
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import json
import re

from app.schemas.scraper import (
    NegativeSearchRequest,
    NegativeSearchResponse,
    NegativeSiteResult
)
from app.services.twogis_parser import random_delay
from app.services.negative_history_db import save_negative_search_result
from ddgs import DDGS

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
}

async def parse_negative_site(url: str, context, request: NegativeSearchRequest) -> NegativeSiteResult:
    domain = urlparse(url).netloc.replace('www.', '')
    
    try:
        page = await context.new_page()
        await page.goto(url, timeout=30000, wait_until='domcontentloaded')
        
        # Небольшая задержка, чтобы скрипты успели отработать
        await random_delay(2, 4)
        
        # Скроллим немного вниз, чтобы подгрузились отзывы
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3)")
        await random_delay(1, 2)
        
        html = await page.content()
        await page.close()
        
        soup = BeautifulSoup(html, 'html.parser')
        
        negative_count = 0
        
        # 1. Попытка найти общую статистику по звездам (часто бывает 1, 2, 3 звезды)
        # Это очень сложно сделать универсально, так как у каждого сайта своя верстка.
        # Поэтому мы перейдем к шагу 2: поиск отзывов на странице.
        
        # 2. Ищем все itemprop="ratingValue"
        rating_tags = soup.find_all(itemprop='ratingValue')
        found_ratings = []
        for tag in rating_tags:
            try:
                val = tag.get('content') or tag.text
                val_float = float(val.replace(',', '.').strip())
                found_ratings.append(val_float)
            except Exception:
                continue
        
        # Дополнительно ищем популярные классы, если itemprop нет
        if not found_ratings:
            # Ищем элементы, текст которых выглядит как "X из 5" или просто "X" внутри блока рейтинга
            potential_ratings = soup.find_all(class_=re.compile(r'rating|star|score', re.I))
            for tag in potential_ratings:
                text = tag.get_text(strip=True)
                match = re.search(r'^(\d[\.,]\d|\d)\s*(?:из|/)\s*(\d)$', text)
                if match:
                    try:
                        found_ratings.append(float(match.group(1).replace(',', '.')))
                    except:
                        pass
        
        # Считаем негатив (меньше 4)
        for r in found_ratings:
            if r <= 3.9:
                negative_count += 1
                
        # Если шкала 10-балльная, то ниже 9 (т.е. <= 8.9) будет негативом, 
        # но мы пока опираемся на самую частую (5 баллов).
        # Как эвристика: если находим оценки больше 5, считаем шкалу 10-балльной
        if any(r > 5 for r in found_ratings):
            negative_count = sum(1 for r in found_ratings if r <= 8.9)
            
        return NegativeSiteResult(
            url=url,
            domain=domain,
            negative_count=negative_count,
            status="success"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при сборе негатива с {url}: {e}")
        return NegativeSiteResult(
            url=url,
            domain=domain,
            negative_count=None,
            status=f"error: {str(e)}"
        )

async def search_negative(request: NegativeSearchRequest):
    yield {"type": "progress", "message": f"Поиск ссылок по кластеру из {len(request.queries)} запросов..."}
    
    links = []
    seen_domains = set()
    
    try:
        def fetch_ddgs(q):
            with DDGS() as ddgs:
                return list(ddgs.text(q, region='ru-ru', max_results=30))
        
        loop = asyncio.get_event_loop()
        for query_str in request.queries:
            query_str = query_str.strip()
            if not query_str: continue
            
            yield {"type": "progress", "message": f"Поиск в DDGS: '{query_str}'..."}
            results = await loop.run_in_executor(None, fetch_ddgs, query_str)
            
            for r in results:
                href = r.get('href')
                if href and href.startswith('http'):
                    domain = urlparse(href).netloc.replace('www.', '')
                    if domain not in seen_domains:
                        seen_domains.add(domain)
                        links.append(href)
                    
        if len(links) == 0:
            yield {"type": "result", "data": NegativeSearchResponse(
                status="error",
                search_query=" | ".join(request.queries),
                error_message="Поисковик не вернул результатов для этих запросов."
            ).dict()}
            return
            
    except Exception as e:
        logger.error(f"Ошибка при поиске через DDGS (Негатив): {e}")
        yield {"type": "result", "data": NegativeSearchResponse(
            status="error",
            search_query=" | ".join(request.queries),
            error_message=f"Ошибка поиска: {e}"
        ).dict()}
        return
        
    links = links[:30] # Ограничиваем до 30
    yield {"type": "progress", "message": f"Найдено {len(links)} сайтов. Начинаем анализ негативных отзывов..."}
    
    site_results = []
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
                tasks = [parse_negative_site(url, context, request) for url in batch]
                batch_results = await asyncio.gather(*tasks)
                site_results.extend(batch_results)
                
            await browser.close()
    except Exception as e:
        logger.error(f"Ошибка при анализе негатива: {e}")
        for url in links[len(site_results):]:
            domain = urlparse(url).netloc.replace('www.', '')
            site_results.append(NegativeSiteResult(url=url, domain=domain, status=f"error (batch fail)"))
    
    response_data = NegativeSearchResponse(
        status="success",
        search_query=" | ".join(request.queries),
        sites=site_results
    ).dict()
    
    try:
        saved_entry = save_negative_search_result(" | ".join(request.queries), response_data)
        response_data['history_id'] = saved_entry['id']
    except Exception as e:
        logger.error(f"Ошибка при сохранении истории негатива в БД: {e}")
        
    # Сохранение в Google Таблицы пока не требуется по запросу пользователя
    
    yield {"type": "result", "data": response_data}
