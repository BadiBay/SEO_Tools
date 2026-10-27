import os
import sys
import json
import uuid
import sqlite3
from loguru import logger
import gspread
from google.oauth2.service_account import Credentials

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_FILE = os.path.join(DATA_DIR, "parser.sqlite3")
CREDENTIALS_FILE = os.path.join(os.path.dirname(BASE_DIR), "credentials.json")
if not os.path.exists(CREDENTIALS_FILE):
    CREDENTIALS_FILE = "credentials.json"

DEFAULT_SPREADSHEET_ID = "1udoJEPFfP-4u_vaZv8jCwtetRDAMq3cKzYC9TR9BHu0"

def restore_from_sheets():
    logger.info("Подключение к Google Sheets...")
    if not os.path.exists(CREDENTIALS_FILE):
        logger.error(f"Файл ключей {CREDENTIALS_FILE} не найден!")
        return

    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ])
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(DEFAULT_SPREADSHEET_ID)

    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Убедимся, что таблицы существуют
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reputation_history (
            id TEXT PRIMARY KEY,
            company TEXT,
            query TEXT,
            timestamp TEXT,
            result TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT,
            links TEXT,
            company TEXT,
            direction TEXT,
            city TEXT,
            address TEXT,
            website TEXT,
            created_at TEXT
        )
    """)
    conn.commit()

    # Считываем уже существующие проекты
    cursor.execute("SELECT id, name, links, company FROM projects")
    existing_projs = {row[1].lower(): {"id": row[0], "name": row[1], "links": json.loads(row[2]) if row[2] else [], "company": row[3]} for row in cursor.fetchall()}

    restored_history = 0
    restored_projects = 0

    worksheets = spreadsheet.worksheets()
    logger.info(f"Найдено листов в Google Таблице: {len(worksheets)}")

    for w in worksheets:
        if w.title in ["Sheet2", "Лист1", "Sheet1"]:
            continue

        company = w.title.strip()
        rows = w.get_all_values()
        if len(rows) < 2:
            continue

        query = rows[1][1] if len(rows[1]) > 1 else ""
        date_str = rows[1][0] if len(rows[1]) > 0 and rows[1][0] else "2026-08-01 12:00:00"

        sites = []
        project_links = []
        for r in rows[1:]:
            if len(r) > 3 and r[3]:
                domain = r[3].strip()
                url = r[4].strip() if len(r) > 4 else ""
                rating = r[5].strip() if len(r) > 5 else ""
                reviews_count = r[6].strip() if len(r) > 6 else ""
                status = r[7].strip() if len(r) > 7 else "success"
                screenshot_url = r[12].strip() if len(r) > 12 else ""

                sites.append({
                    "domain": domain,
                    "url": url,
                    "rating": rating,
                    "reviews_count": reviews_count,
                    "status": status,
                    "screenshot_url": screenshot_url
                })
                if url and ("yandex" in url or "2gis" in url or "google" in url):
                    project_links.append(url)

        # 1. Сохраняем в reputation_history
        hist_id = str(uuid.uuid4())
        res_payload = {
            "company": company,
            "query": query,
            "sites": sites
        }
        
        # Проверяем, есть ли уже такая запись
        cursor.execute("SELECT id FROM reputation_history WHERE company = ?", (company,))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO reputation_history (id, company, query, timestamp, result) VALUES (?, ?, ?, ?, ?)",
                (hist_id, company, query, date_str, json.dumps(res_payload, ensure_ascii=False))
            )
            restored_history += 1

        # 2. Добавляем в проекты, если его ещё нет
        company_key = company.lower()
        if company_key not in existing_projs:
            proj_id = str(uuid.uuid4())
            # Выделяем первые ссылки
            links_to_save = project_links[:5] if project_links else [s["url"] for s in sites[:3] if s.get("url")]
            cursor.execute(
                "INSERT INTO projects (id, name, links, company, direction, city, address, website, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    proj_id,
                    company,
                    json.dumps(links_to_save, ensure_ascii=False),
                    company,
                    "",
                    "",
                    "",
                    "",
                    date_str + "Z"
                )
            )
            existing_projs[company_key] = {"id": proj_id, "name": company, "links": links_to_save}
            restored_projects += 1

    conn.commit()
    conn.close()

    # Обновляем projects.json для согласованности
    proj_list = []
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    for row in conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall():
        proj_list.append({
            "id": row["id"],
            "name": row["name"],
            "links": json.loads(row["links"]) if row["links"] else [],
            "company": row["company"],
            "direction": row["direction"],
            "city": row["city"],
            "address": row["address"],
            "website": row["website"],
            "created_at": row["created_at"]
        })
    conn.close()

    proj_file = os.path.join(DATA_DIR, "projects.json")
    with open(proj_file, "w", encoding="utf-8") as f:
        json.dump(proj_list, f, ensure_ascii=False, indent=2)

    logger.success(f"Готово! Восстановлено проектов: {restored_projects}, записей истории: {restored_history}.")
    logger.info(f"Всего проектов в базе теперь: {len(proj_list)}")

if __name__ == "__main__":
    restore_from_sheets()
