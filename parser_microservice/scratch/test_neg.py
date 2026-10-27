import httpx
import asyncio

async def test():
    async with httpx.AsyncClient() as client:
        r = await client.post('http://localhost:8000/api/v1/negative/search', json={'queries': ['test query']})
        print(r.status_code)
        print(r.text)

asyncio.run(test())
