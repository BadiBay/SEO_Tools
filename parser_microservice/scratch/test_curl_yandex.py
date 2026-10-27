from curl_cffi import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

def search_yandex(query):
    url = f"https://yandex.ru/search/?text={quote(query)}"
    print(f"Searching: {url}")
    
    # We use impersonate="chrome110" to bypass TLS fingerprinting
    resp = requests.get(url, impersonate="chrome110", timeout=15)
    print(f"Status: {resp.status_code}")
    
    if "showcaptcha" in resp.url or "captcha" in resp.text.lower():
        print("CAPTCHA detected!")
        return
        
    soup = BeautifulSoup(resp.text, 'html.parser')
    links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.startswith('http') and 'yandex' not in href:
            links.append(href)
            
    print(f"Found {len(links)} links:")
    for l in links[:15]:
        print(l)

if __name__ == "__main__":
    search_yandex("стоматология весна отзывы")
