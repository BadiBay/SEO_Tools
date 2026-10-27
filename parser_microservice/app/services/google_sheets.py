import os
from datetime import datetime
from typing import List, Dict, Any
import gspread
from google.oauth2.service_account import Credentials
from loguru import logger

# Настройки для Google Sheets
CREDENTIALS_FILE = "credentials.json"
DEFAULT_SPREADSHEET_ID = "1udoJEPFfP-4u_vaZv8jCwtetRDAMq3cKzYC9TR9BHu0"

# Области доступа для API
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def _get_gspread_client() -> gspread.Client:
    """Инициализирует и возвращает клиент gspread."""
    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError(f"Файл ключей {CREDENTIALS_FILE} не найден. Убедитесь, что он лежит в корне проекта.")
    
    credentials = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    client = gspread.authorize(credentials)
    return client

def init_sheet_headers(worksheet: gspread.Worksheet):
    """Инициализирует заголовки, если таблица пустая."""
    # Проверяем, есть ли уже данные в первой строке
    first_row = worksheet.row_values(1)
    if not first_row:
        headers = ["Дата поиска", "Запрос", "Компания", "Домен", "Ссылка", "Рейтинг", "Количество отзывов", "Статус парсинга", "Было отзывов", "Был рейтинг", "Изменение рейтинга", "Изменение отзывов", "Скриншот"]
        worksheet.append_row(headers)
        # Опционально: можно сделать заголовки жирными
        try:
            worksheet.format("A1:M1", {"textFormat": {"bold": True}})
        except Exception:
            pass

def append_reputation_results_to_sheet(company: str, query: str, search_result: Dict[str, Any], spreadsheet_id: str = DEFAULT_SPREADSHEET_ID):
    """
    Записывает результаты поиска в Google Таблицу.
    """
    try:
        client = _get_gspread_client()
        spreadsheet = client.open_by_key(spreadsheet_id)
        
        # Ищем лист с именем компании, если нет - создаем
        sheet_title = company[:100] if company else "Без названия"
        try:
            worksheet = spreadsheet.worksheet(sheet_title)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=sheet_title, rows=100, cols=20)
            logger.info(f"Создан новый лист '{sheet_title}' в Google Таблице.")
            
            # Добавляем круговую диаграмму для распределения рейтингов
            try:
                sheet_id = worksheet.id
                body = {
                    "requests": [
                        {
                            "addChart": {
                                "chart": {
                                    "spec": {
                                        "title": "Распределение рейтингов",
                                        "pieChart": {
                                            "legendPosition": "BOTTOM_LEGEND",
                                            "domain": {
                                                "sourceRange": {
                                                    "sources": [{
                                                        "sheetId": sheet_id,
                                                        "startRowIndex": 1,
                                                        "endRowIndex": 4,
                                                        "startColumnIndex": 14,
                                                        "endColumnIndex": 15
                                                    }]
                                                }
                                            },
                                            "series": {
                                                "sourceRange": {
                                                    "sources": [{
                                                        "sheetId": sheet_id,
                                                        "startRowIndex": 1,
                                                        "endRowIndex": 4,
                                                        "startColumnIndex": 15,
                                                        "endColumnIndex": 16
                                                    }]
                                                }
                                            }
                                        }
                                    },
                                    "position": {
                                        "overlayPosition": {
                                            "anchorCell": {
                                                "sheetId": sheet_id,
                                                "rowIndex": 1,
                                                "columnIndex": 16
                                            },
                                            "offsetXPixels": 10,
                                            "offsetYPixels": 10,
                                            "widthPixels": 450,
                                            "heightPixels": 300
                                        }
                                    }
                                }
                            }
                        }
                    ]
                }
                spreadsheet.batch_update(body)
                logger.info(f"Круговая диаграмма успешно добавлена на лист '{sheet_title}'.")
            except Exception as e:
                logger.error(f"Ошибка при добавлении диаграммы в Google Sheets: {e}")
        
        # Инициализируем заголовки, если таблица пустая
        init_sheet_headers(worksheet)
        
        existing_rows = worksheet.get_all_values()
        headers = existing_rows[0] if existing_rows else ["Дата поиска", "Запрос", "Компания", "Домен", "Ссылка", "Рейтинг", "Количество отзывов", "Статус парсинга", "Было отзывов", "Был рейтинг", "Изменение рейтинга", "Изменение отзывов", "Скриншот"]
        
        # Формируем словарь существующих строк (ключ - домен, index 3)
        existing_dict = {}
        for row in existing_rows[1:]:
            if len(row) > 3:
                domain_key = row[3]
                existing_dict[domain_key] = row
        
        date_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        sites = search_result.get("sites", [])
        
        if not sites and not existing_dict:
            logger.warning(f"Нет сайтов для сохранения в Google Таблицу для запроса '{query}'")
            return
        
        # Обновляем существующие или добавляем новые
        for site in sites:
            domain_key = site.get("domain", "")
            row = [
                date_str,
                query,
                company,
                domain_key,
                site.get("url", ""),
                site.get("rating", ""),
                site.get("reviews_count", ""),
                site.get("status", ""),
                site.get("previous_reviews_count", ""),
                site.get("previous_rating", ""),
                site.get("rating_change", ""),
                site.get("reviews_count_change", ""),
                site.get("screenshot_url", "")
            ]
            existing_dict[domain_key] = row
            
        # Удаляем из existing_dict те сайты, которых нет в новом результате (для текущего запроса)
        new_domains = set(site.get("domain", "") for site in sites)
        keys_to_delete = []
        for domain, row in existing_dict.items():
            if len(row) > 1 and row[1] == query: # совпадает запрос
                if domain not in new_domains:
                    keys_to_delete.append(domain)
        
        for k in keys_to_delete:
            del existing_dict[k]
        
        all_rows = [headers] + list(existing_dict.values())
        
        positive = neutral = negative = 0
        for row in existing_dict.values():
            if len(row) > 5 and row[5]:
                try:
                    r = float(str(row[5]).replace(',', '.'))
                    if r >= 4.5: positive += 1
                    elif r >= 4.0: neutral += 1
                    else: negative += 1
                except ValueError:
                    pass

        for i in range(len(all_rows)):
            while len(all_rows[i]) < 16:
                all_rows[i].append("")

        all_rows[0][14] = "Категория"
        all_rows[0][15] = "Количество"
        
        while len(all_rows) < 4:
            all_rows.append([""] * 16)
            
        all_rows[1][14] = "Позитивные (>= 4.5)"
        all_rows[1][15] = positive
        all_rows[2][14] = "Нейтральные (4.0 - 4.49)"
        all_rows[2][15] = neutral
        all_rows[3][14] = "Негативные (< 4.0)"
        all_rows[3][15] = negative
        
        # Перезаписываем лист (очищаем и вставляем все строки разом)
        worksheet.clear()
        worksheet.append_rows(all_rows)
        logger.info(f"Успешно перезаписано {len(all_rows) - 1} уникальных строк в Google Таблицу для '{company}'.")
            
    except FileNotFoundError as e:
        logger.error(str(e))
    except gspread.exceptions.APIError as e:
        logger.error(f"Ошибка API Google Sheets (возможно, нет доступа к таблице): {e}")
    except Exception as e:
        logger.error(f"Неизвестная ошибка при сохранении в Google Таблицы: {repr(e)}")

def init_competitors_sheet_headers(worksheet: gspread.Worksheet):
    """Инициализирует заголовки для конкурентов, если таблица пустая."""
    first_row = worksheet.row_values(1)
    if not first_row:
        headers = ["Дата", "Запрос", "Название конкурента", "URL", "Рейтинг", "Количество отзывов", "Реклама", "Тип рекламы", "Негативные отзывы"]
        worksheet.append_row(headers)
        try:
            worksheet.format("A1:I1", {"textFormat": {"bold": True}})
        except Exception:
            pass

def append_competitors_results_to_sheet(query: str, competitors: List[Dict[str, Any]], spreadsheet_id: str = "1eng4RIv-4QN4Da2tnpif2q1p83zTfkNdgLYPsoYZBnk"):
    """
    Записывает результаты анализа конкурентов в Google Таблицу.
    """
    try:
        client = _get_gspread_client()
        spreadsheet = client.open_by_key(spreadsheet_id)
        
        # Ищем лист с именем запроса
        sheet_title = query[:100] if query else "Без названия"
        try:
            worksheet = spreadsheet.worksheet(sheet_title)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=sheet_title, rows=100, cols=8)
            logger.info(f"Создан новый лист '{sheet_title}' в Google Таблице конкурентов.")
            
        init_competitors_sheet_headers(worksheet)
        
        existing_rows = worksheet.get_all_values()
        headers = existing_rows[0] if existing_rows else ["Дата", "Запрос", "Название конкурента", "URL", "Рейтинг", "Количество отзывов", "Реклама", "Тип рекламы", "Негативные отзывы"]
        
        # Формируем словарь существующих строк (ключ - URL, index 3)
        existing_dict = {}
        for row in existing_rows[1:]:
            if len(row) > 3:
                url_key = row[3]
                existing_dict[url_key] = row
        
        date_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        
        if not competitors and not existing_dict:
            logger.warning(f"Нет конкурентов для сохранения в Google Таблицу для запроса '{query}'")
            return
            
        for comp in competitors:
            is_ad_str = "Да" if comp.get("is_ad") else "Нет"
            
            neg_reviews = comp.get("top_negative_reviews", [])
            neg_reviews_text = "\n\n".join([f"({r.get('rating')}★) {r.get('text')}" for r in neg_reviews]) if neg_reviews else ""
            
            url_key = comp.get("url", "")
            row = [
                date_str,
                query,
                comp.get("name", ""),
                url_key,
                str(comp.get("rating", "")),
                str(comp.get("reviews_count", "")),
                is_ad_str,
                comp.get("ad_type", ""),
                neg_reviews_text
            ]
            existing_dict[url_key] = row
            
        all_rows = [headers] + list(existing_dict.values())
        
        worksheet.clear()
        worksheet.append_rows(all_rows)
        logger.info(f"Успешно перезаписано {len(all_rows) - 1} уникальных строк в таблицу конкурентов для '{query}'.")
            
    except Exception as e:
        logger.error(f"Ошибка при сохранении конкурентов в Google Таблицы: {repr(e)}")
