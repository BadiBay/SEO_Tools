from ddgs import AsyncDDGS
import asyncio

async def test_async_ddgs():
    try:
        async with AsyncDDGS() as ddgs:
            results = await ddgs.atext("стоматология весна отзывы", max_results=10)
            print(f"Found {len(results)} links")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_async_ddgs())
