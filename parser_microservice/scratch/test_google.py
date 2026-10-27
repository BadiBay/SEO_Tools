from googlesearch import search
import time

try:
    results = search("стоматология весна отзывы", num_results=20, lang="ru")
    print("Found links:")
    for r in results:
        print(r)
except Exception as e:
    print(f"Error: {e}")
