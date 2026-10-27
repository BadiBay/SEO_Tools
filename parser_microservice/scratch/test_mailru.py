import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from urllib.parse import quote, urlparse

async def search_mailru(query: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        url = f"https://go.mail.ru/search?q={quote(query)}"
        print(f"Going to {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        
        await asyncio.sleep(2)
        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        print(f"HTML snippet: {html[:1000]}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(search_mailru("стоматология весна отзывы"))
