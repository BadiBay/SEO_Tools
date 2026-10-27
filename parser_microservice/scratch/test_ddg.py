import asyncio
import httpx
from bs4 import BeautifulSoup
from urllib.parse import quote, urlparse

async def search_ddg(query: str):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
    
    async with httpx.AsyncClient(headers=headers, timeout=10.0) as client:
        resp = await client.get(url)
        print(f"Status: {resp.status_code}")
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        links = []
        for a in soup.find_all('a', class_='result__url'):
            href = a.get('href')
            if href:
                # DDG links are usually actual urls in the text, or we can get the href
                links.append(href)
                
        print(f"Found {len(links)} links:")
        for l in links[:5]:
            print(l)

if __name__ == "__main__":
    asyncio.run(search_ddg("стоматология весна отзывы"))
