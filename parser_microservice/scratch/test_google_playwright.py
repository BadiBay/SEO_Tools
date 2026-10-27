import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from urllib.parse import quote, urlparse

async def search_google(query: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        url = f"https://www.google.com/search?q={quote(query)}"
        print(f"Going to {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        
        # Accept cookies if asked
        try:
            await page.click('button:has-text("Accept all")', timeout=3000)
        except:
            pass
            
        await asyncio.sleep(2)
        await page.screenshot(path="scratch/google.png")
        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            # google organic links usually don't contain google.com
            if href.startswith('http') and 'google' not in href.lower():
                # We need to filter out some trash
                links.append(href)
                
        print(f"Found {len(links)} links:")
        for l in links[:15]:
            print(l)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(search_google("стоматология весна отзывы"))
