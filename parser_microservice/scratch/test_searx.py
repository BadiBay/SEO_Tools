import asyncio
import httpx
from urllib.parse import quote

async def test_searx():
    instances = [
        "https://searx.be",
        "https://search.ononoki.org",
        "https://searx.mha.fi",
    ]
    query = "стоматология весна отзывы"
    
    for instance in instances:
        url = f"{instance}/search?q={quote(query)}&format=json"
        print(f"Trying {url} ...")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                print(f"Status: {resp.status_code}")
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get('results', [])
                    print(f"Found {len(results)} links")
                    for r in results[:5]:
                        print(r.get('url'))
                    return
        except Exception as e:
            print(f"Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_searx())
