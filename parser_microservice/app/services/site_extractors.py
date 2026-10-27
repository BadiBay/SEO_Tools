from bs4 import BeautifulSoup
import re
from typing import Tuple, Optional
import json

def _get_number(text: str) -> Optional[int]:
    if not text: return None
    nums = re.findall(r'\d+', text.replace(' ', '').replace('\xa0', ''))
    return int(nums[0]) if nums else None

def _get_float(text: str) -> Optional[float]:
    if not text: return None
    m = re.search(r'\d[\.,]\d|\d', text)
    return float(m.group().replace(',', '.')) if m else None

def extract_zoon(soup: BeautifulSoup) -> Tuple[Optional[float], Optional[int]]:
    r, c = None, None
    r_tag = soup.select_one('.rating-value, .stars-rating__value, [data-ui="rating-value"]')
    if r_tag: r = _get_float(r_tag.text)
    
    c_tags = soup.select('.list-reviews-count, .fs-large, a[href*="reviews"] span, [data-type="reviews"] span')
    for tag in c_tags:
        if c := _get_number(tag.text): break
            
    if c is None:
        if m := re.search(r'(\d+)\s*(?:отзыв|оцен)', soup.get_text(separator=' ').lower()):
            c = int(m.group(1))
    return r, c

def extract_prodoctorov(soup: BeautifulSoup) -> Tuple[Optional[float], Optional[int]]:
    r_tag = soup.select_one('.ui-text-rating, .l-doctor-details__rating, .rating-num, .b-doctor-rating__val')
    c_tag = soup.select_one('.b-doctor-details__reviews-count, .ui-text-reviews, [href="#reviews"]')
    return _get_float(r_tag.text) if r_tag else None, _get_number(c_tag.text) if c_tag else None

def extract_flamp(soup: BeautifulSoup) -> Tuple[Optional[float], Optional[int]]:
    r_tag = soup.select_one('.filial-rating__value, .rating-badge, .score')
    c_tag = soup.select_one('.filial-rating__reviews-count, .reviews-count, a[href="#reviews"]')
    return _get_float(r_tag.text) if r_tag else None, _get_number(c_tag.text) if c_tag else None

def extract_hh(soup: BeautifulSoup) -> Tuple[Optional[float], Optional[int]]:
    r_tag = soup.select_one('[data-qa="employer-rating"], .employer-rating, .employer-index-rating')
    c_tag = soup.select_one('[data-qa="employer-reviews-count"], .reviews-count')
    return _get_float(r_tag.text) if r_tag else None, _get_number(c_tag.text) if c_tag else None

def extract_napopravku(soup: BeautifulSoup) -> Tuple[Optional[float], Optional[int]]:
    r_tag = soup.select_one('.clinic-rating__value, .profile-rating__value, .rating-value')
    c_tag = soup.select_one('.clinic-rating__count, .profile-rating__count, .reviews-count')
    return _get_float(r_tag.text) if r_tag else None, _get_number(c_tag.text) if c_tag else None

def extract_yell(soup: BeautifulSoup) -> Tuple[Optional[float], Optional[int]]:
    r_tag = soup.select_one('.company-rating__value, .rating__value')
    c_tag = soup.select_one('.company-rating__reviews, .rating__reviews')
    return _get_float(r_tag.text) if r_tag else None, _get_number(c_tag.text) if c_tag else None

def extract_doctu(soup: BeautifulSoup) -> Tuple[Optional[float], Optional[int]]:
    r_tag = soup.select_one('.rating-value, .doctor-rating')
    c_tag = soup.select_one('.reviews-count, [href="#reviews"]')
    return _get_float(r_tag.text) if r_tag else None, _get_number(c_tag.text) if c_tag else None

def extract_med(soup: BeautifulSoup) -> Tuple[Optional[float], Optional[int]]:
    # Универсальный парсер для мед. сайтов (kleos, krasotaimedicina, infodoctor)
    r = _get_float((soup.select_one('[itemprop="ratingValue"]') or soup.select_one('.rating, .score')).text if soup.select_one('[itemprop="ratingValue"], .rating, .score') else "")
    c = _get_number((soup.select_one('[itemprop="reviewCount"]') or soup.select_one('.reviews, .comments')).text if soup.select_one('[itemprop="reviewCount"], .reviews, .comments') else "")
    return r, c

def extract_stom(soup: BeautifulSoup) -> Tuple[Optional[float], Optional[int]]:
    # Для stom-firms, stomotologiya, 32top, startsmile
    r_tag = soup.select_one('.rating__value, .score, .stars')
    c_tag = soup.select_one('.reviews__count, .comments-count, a[href*="review"]')
    return _get_float(r_tag.text) if r_tag else None, _get_number(c_tag.text) if c_tag else None

def extract_directories(soup: BeautifulSoup) -> Tuple[Optional[float], Optional[int]]:
    # Для spr.ru, checko.ru, totadres.ru, rting.ru
    r = _get_float((soup.select_one('.rating, .org-rating, [itemprop="ratingValue"]') or soup.new_tag("div")).text)
    c = _get_number((soup.select_one('.reviews, .org-reviews, [itemprop="reviewCount"]') or soup.new_tag("div")).text)
    return r, c

# Реестр экстракторов
SITE_EXTRACTORS = {
    'zoon.ru': extract_zoon,
    'prodoctorov.ru': extract_prodoctorov,
    'flamp.ru': extract_flamp,
    'hh.ru': extract_hh,
    'napopravku.ru': extract_napopravku,
    'yell.ru': extract_yell,
    'doctu.ru': extract_doctu,
    'kleos.ru': extract_med,
    'medicaladvice.ru': extract_med,
    'krasotaimedicina.ru': extract_med,
    'infodoctor.ru': extract_med,
    'medadvisor.ru': extract_med,
    'vrachi-goroda.ru': extract_med,
    'stom-firms.ru': extract_stom,
    'stomotologiya.ru': extract_stom,
    'dentistfind.ru': extract_stom,
    '32top.ru': extract_stom,
    'startsmile.ru': extract_stom,
    'ortopatnomogramma.ru': extract_stom,
    'topdent.ru': extract_stom,
    'totadres.ru': extract_directories,
    'rting.ru': extract_directories,
    'otzovy-moskvy.ru': extract_directories,
    'rating.msk.ru': extract_directories,
    'spr.ru': extract_directories,
    'kinf.ru': extract_directories,
    'checko.ru': extract_directories,
    '2gis.ru': extract_directories,
    'yandex.ru': extract_directories,
    'yandex.com': extract_directories,
}

def try_extract_specific(domain: str, soup: BeautifulSoup) -> Tuple[Optional[float], Optional[int]]:
    domain = domain.lower().replace('www.', '')
    
    if domain in SITE_EXTRACTORS:
        return SITE_EXTRACTORS[domain](soup)
        
    parts = domain.split('.')
    if len(parts) > 2:
        root_domain = f"{parts[-2]}.{parts[-1]}"
        if root_domain in SITE_EXTRACTORS:
            return SITE_EXTRACTORS[root_domain](soup)
            
    return None, None
