import asyncio
import httpx
from bs4 import BeautifulSoup
from loguru import logger
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import json

from app.schemas.scraper import (
    MentionsSearchRequest,
    MentionsSearchResponse,
    MentionSiteResult
)
from app.services.mentions_history_db import save_mentions_search_result
from ddgs import DDGS

async def check_link_presence(url: str, website: str, context) -> tuple[bool, str]:
    """
    Переходит по URL с помощью Playwright, проверяет наличие website в HTML или тексте.
    Возвращает (is_link_present, title).
    """
    domain = urlparse(website).netloc.replace('www.', '')
    if not domain:
         domain = website.replace('www.', '').replace('http://', '').replace('https://', '').split('/')[0]

    page = None
    title = ""
    is_link_present = False
    try:
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        
        # Ждем немного
        await asyncio.sleep(2)
        
        title = await page.title()
        
        # Проверяем наличие домена искомого сайта в href или тексте
        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        for a in soup.find_all('a', href=True):
            if domain.lower() in a['href'].lower():
                is_link_present = True
                break
        
        if not is_link_present:
            # Ищем просто упоминание текстом
            if domain.lower() in html.lower():
                is_link_present = True
                
        return is_link_present, title
    except Exception as e:
        logger.debug(f"Ошибка при проверке ссылки на {url}: {e}")
        return False, title
    finally:
        if page:
            await page.close()


async def process_mention_site(url: str, title: str, snippet: str, request: MentionsSearchRequest, context) -> MentionSiteResult:
    domain = urlparse(url).netloc.replace('www.', '')
    
    # Пытаемся проверить наличие ссылки с помощью Playwright
    is_present, page_title = await check_link_presence(url, request.website, context)
    
    # Если заголовок с поиска пустой, берем со страницы
    final_title = page_title if not title else title

    return MentionSiteResult(
        url=url,
        domain=domain,
        title=final_title,
        snippet=snippet,
        is_link_present=is_present,
        status="success"
    )

async def search_mentions(request: MentionsSearchRequest):
    website_domain = urlparse(request.website).netloc.replace('www.', '')
    if not website_domain:
        website_domain = request.website.replace('www.', '').replace('http://', '').replace('https://', '').split('/')[0]
        
    city_part = f" {request.city}" if request.city else ""
    search_query = f'{request.company}{city_part} "{website_domain}"'
    
    logger.info(f"Сформирован запрос поиска упоминаний: '{search_query}'")
    yield {"type": "progress", "message": f"Сформирован поисковой запрос: '{search_query}'"}
    
    links_data = []
    seen_domains = set()
    
    yield {"type": "progress", "message": "Ищем упоминания в поисковике..."}
    try:
        loop = asyncio.get_event_loop()
        def _do_search():
            with DDGS() as ddgs:
                return [r for r in ddgs.text(search_query, max_results=30)]
                
        results = await loop.run_in_executor(None, _do_search)
        
        for r in results:
            href = r.get('href', '')
            title = r.get('title', '')
            snippet = r.get('body', '')
            
            if href.startswith('http'):
                domain = urlparse(href).netloc.replace('www.', '')
                if domain not in seen_domains:
                    seen_domains.add(domain)
                    links_data.append({"url": href, "title": title, "snippet": snippet})
                    
        if len(links_data) == 0:
            yield {"type": "result", "data": MentionsSearchResponse(
                status="error",
                search_query=search_query,
                error_message="Поисковик не вернул результатов для этого запроса."
            ).dict()}
            return
            
    except Exception as e:
        logger.error(f"Ошибка при поиске через DDGS (упоминания): {e}")
        yield {"type": "result", "data": MentionsSearchResponse(
            status="error",
            search_query=search_query,
            error_message=f"Ошибка поиска: {e}"
        ).dict()}
        return
        
    links_data = links_data[:30] # Ограничиваем до 30
    yield {"type": "progress", "message": f"Найдено {len(links_data)} сайтов. Начинаем проверку наличия ссылок..."}
    logger.info(f"Найдено {len(links_data)} сайтов. Начинаем проверку...")
    
    sites_results = []
    
    try:
        async with Stealth().use_async(async_playwright()) as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            
            batch_size = 5
            total_batches = (len(links_data) + batch_size - 1) // batch_size
            for i in range(0, len(links_data), batch_size):
                batch_num = i // batch_size + 1
                batch = links_data[i:i+batch_size]
                yield {"type": "progress", "message": f"Проверка сайтов (пачка {batch_num} из {total_batches})..."}
                
                tasks = [
                    process_mention_site(
                        item["url"], 
                        item["title"], 
                        item["snippet"], 
                        request, 
                        context
                    ) for item in batch
                ]
                
                batch_results = await asyncio.gather(*tasks)
                sites_results.extend(batch_results)
                
            await browser.close()
    except Exception as e:
        logger.error(f"Ошибка при проверке сайтов: {e}")
        # Заполняем оставшиеся ссылки ошибками
        for item in links_data[len(sites_results):]:
            domain = urlparse(item["url"]).netloc.replace('www.', '')
            sites_results.append(MentionSiteResult(
                url=item["url"],
                domain=domain,
                title=item["title"],
                snippet=item["snippet"],
                status=f"error (batch fail)"
            ))
            
    response_data = MentionsSearchResponse(
        status="success",
        search_query=search_query,
        sites=sites_results
    ).dict()
    
    # Сохраняем в локальную БД
    try:
        save_mentions_search_result(request.company, search_query, response_data)
    except Exception as e:
        logger.error(f"Ошибка при сохранении истории упоминаний в БД: {e}")
        
    yield {"type": "result", "data": response_data}
