import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.google_sheets import append_reputation_results_to_sheet

test_data = {
    "status": "success",
    "website_title": "Test Company",
    "search_query": "Test search query",
    "sites": [
        {"domain": "yandex.ru", "url": "https://yandex.ru", "rating": 4.5, "reviews_count": 10, "status": "success"},
        {"domain": "2gis.ru", "url": "https://2gis.ru", "rating": 5.0, "reviews_count": 2, "status": "success"}
    ]
}

print("Testing Google Sheets integration...")
import traceback
try:
    append_reputation_results_to_sheet("Test Company", "Test search query", test_data)
except Exception as e:
    traceback.print_exc()
print("Done. Check the Google Sheet.")
