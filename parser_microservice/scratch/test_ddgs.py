from ddgs import DDGS
import json

try:
    with DDGS() as ddgs:
        results = ddgs.text("стоматология весна отзывы", max_results=10)
        links = []
        for r in results:
            links.append(r['href'])
            
        print(f"Found {len(links)} links:")
        for l in links:
            print(l)
except Exception as e:
    print(e)
