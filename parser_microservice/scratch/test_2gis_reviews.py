import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        await page.goto("https://go.2gis.com/LAia8", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(5)
        
        # Нажимаем на "Отзывы"
        for selector in ["div:has-text('Отзывы')", "a:has-text('Отзывы')", "span:has-text('Отзывы')"]:
            elements = await page.locator(selector).all()
            for el in elements:
                if await el.is_visible():
                    try:
                        await el.click()
                        print("Кликнули на отзывы!")
                        break
                    except Exception as e:
                        pass
        
        await asyncio.sleep(5)
        
        text = await page.evaluate("document.body.innerText")
        print(text[:2000])
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
