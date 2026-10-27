import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from urllib.parse import quote

async def search_ddg_playwright(query: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        url = f"https://duckduckgo.com/?q={quote(query)}&t=h_&ia=web"
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        
        await asyncio.sleep(2)
        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith('http') and 'duckduckgo' not in href:
                links.append(href)
                
        print(f"Found {len(links)} links:")
        for l in links[:10]:
            print(l)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(search_ddg_playwright("стоматология весна отзывы"))
