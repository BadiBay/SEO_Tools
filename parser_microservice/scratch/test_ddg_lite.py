import asyncio
import httpx
from bs4 import BeautifulSoup

async def search_ddg_lite(query: str):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    url = "https://lite.duckduckgo.com/lite/"
    data = {"q": query}
    
    async with httpx.AsyncClient(headers=headers, timeout=10.0) as client:
        resp = await client.post(url, data=data)
        print(f"Status: {resp.status_code}")
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        links = []
        for a in soup.find_all('a'):
            href = a.get('href')
            if href and href.startswith('http'):
                links.append(href)
                
        print(f"Found {len(links)} links:")
        for l in links[:10]:
            print(l)

if __name__ == "__main__":
    asyncio.run(search_ddg_lite("стоматология весна отзывы"))
