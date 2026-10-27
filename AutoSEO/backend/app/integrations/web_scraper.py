"""
Web Scraper Adapter — парсинг контента страниц, проверка ссылок, скачивание медиа.
"""
import re
import httpx
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import Optional


@dataclass
class PageContent:
    """Распарсенный контент страницы."""
    url: str
    status_code: int
    title: str = ""
    h1: str = ""
    meta_description: str = ""
    text_content: str = ""
    favicon_url: str = ""
    logo_url: str = ""


class WebScraperAdapter:
    """Утилита для скрапинга веб-страниц."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

    async def fetch_page(self, url: str) -> PageContent:
        """Скачать и распарсить страницу."""
        async with httpx.AsyncClient(
            timeout=self.timeout,
            headers=self.headers,
            follow_redirects=True,
        ) as client:
            resp = await client.get(url)

            if resp.status_code != 200:
                return PageContent(url=url, status_code=resp.status_code)

            soup = BeautifulSoup(resp.text, "lxml")

            title = soup.title.string.strip() if soup.title and soup.title.string else ""
            h1_tag = soup.find("h1")
            h1 = h1_tag.get_text(strip=True) if h1_tag else ""

            meta_desc = ""
            meta_tag = soup.find("meta", attrs={"name": "description"})
            if meta_tag:
                meta_desc = meta_tag.get("content", "")

            # Текст страницы (без скриптов/стилей)
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = soup.get_text(separator=" ", strip=True)[:3000]

            # Favicon
            favicon = ""
            fav_link = soup.find("link", rel=lambda r: r and "icon" in r)
            if fav_link:
                favicon = fav_link.get("href", "")
                if favicon and not favicon.startswith("http"):
                    from urllib.parse import urljoin
                    favicon = urljoin(url, favicon)

            # Logo (эвристика — ищем img с "logo" в src/class/alt)
            logo = ""
            for img in soup.find_all("img"):
                src = img.get("src", "")
                alt = img.get("alt", "").lower()
                cls = " ".join(img.get("class", []))
                if "logo" in src.lower() or "logo" in alt or "logo" in cls.lower():
                    logo = src
                    if logo and not logo.startswith("http"):
                        from urllib.parse import urljoin
                        logo = urljoin(url, logo)
                    break

            return PageContent(
                url=url,
                status_code=resp.status_code,
                title=title,
                h1=h1,
                meta_description=meta_desc,
                text_content=text,
                favicon_url=favicon,
                logo_url=logo,
            )

    async def check_url_alive(self, url: str) -> tuple[bool, int]:
        """Проверить доступность URL. Возвращает (is_alive, http_code)."""
        try:
            async with httpx.AsyncClient(
                timeout=15,
                headers=self.headers,
                follow_redirects=True,
            ) as client:
                resp = await client.head(url)
                return resp.status_code == 200, resp.status_code
        except Exception:
            return False, 0

    async def get_domain_age(self, domain: str) -> Optional[int]:
        """Определить возраст домена через WHOIS. Возвращает лет."""
        try:
            import whois
            from datetime import datetime, timezone
            w = whois.whois(domain)
            creation = w.creation_date
            if isinstance(creation, list):
                creation = creation[0]
            if creation:
                age = (datetime.now(timezone.utc) - creation.replace(tzinfo=timezone.utc)).days // 365
                return max(0, age)
        except Exception:
            pass
        return None

    @staticmethod
    def is_junk_alt(alt_text: str) -> bool:
        """
        Проверка: является ли alt-тег «мусорным» (техническое имя файла).
        Маркеры: расширение файла, image/frame/photo/group/scale,
        только цифры/спецсимволы.
        """
        if not alt_text or not alt_text.strip():
            return True

        alt = alt_text.strip().lower()

        # Содержит расширение файла
        file_ext_pattern = r'\.(jpg|jpeg|png|gif|webp|svg|bmp|ico|tiff)(\s|$)'
        if re.search(file_ext_pattern, alt):
            return True

        # Слова-маркеры мусора
        junk_markers = [
            "image", "img", "frame", "photo", "group", "scale",
            "screenshot", "picture", "untitled", "noname",
            "dsc_", "dsc-", "img_", "img-",
        ]
        for marker in junk_markers:
            if marker in alt:
                return True

        # Только цифры, дефисы, подчёркивания и точки
        if re.match(r'^[\d\-_.\s]+$', alt):
            return True

        # Совпадает с типичным именем файла
        if re.match(r'^[a-z0-9_\-]+\s*$', alt) and len(alt) < 30:
            # Если нет пробелов и выглядит как имя файла
            if "_" in alt or "-" in alt:
                return True

        return False
