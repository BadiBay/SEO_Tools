import sqlite3
import os
import json
from loguru import logger
from typing import List, Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_FILE = os.path.join(DATA_DIR, "parser.sqlite3")

def get_db_connection() -> sqlite3.Connection:
    if not os.path.exists(DATA_DIR):
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create DATA_DIR '{DATA_DIR}': {e}")
    try:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to SQLite DB at '{DB_FILE}': {e}")
        raise

def init_db():
    logger.info("Initializing SQLite database...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Репутация
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reputation_history (
            id TEXT PRIMARY KEY,
            company TEXT,
            query TEXT,
            timestamp TEXT,
            result TEXT
        )
    """)
    
    # Упоминания
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mentions_history (
            id TEXT PRIMARY KEY,
            company TEXT,
            query TEXT,
            timestamp TEXT,
            result TEXT
        )
    """)
    
    # Негатив
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS negative_history (
            id TEXT PRIMARY KEY,
            query TEXT,
            timestamp TEXT,
            result TEXT
        )
    """)
    
    # Конкуренты
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS competitors_history (
            id TEXT PRIMARY KEY,
            query TEXT,
            timestamp TEXT,
            result TEXT
        )
    """)
    
    # Проекты
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
    conn.close()
    
    _migrate_old_json_files()

def _migrate_old_json_files():
    """Migrates old JSON files to SQLite once."""
    migrated_flag = os.path.join(DATA_DIR, ".migrated_to_sqlite")
    if os.path.exists(migrated_flag):
        return
        
    logger.info("Running JSON to SQLite migration...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Reputation
    rep_file = os.path.join(DATA_DIR, "reputation_history.json")
    if os.path.exists(rep_file):
        try:
            with open(rep_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    cursor.execute(
                        "INSERT OR IGNORE INTO reputation_history (id, company, query, timestamp, result) VALUES (?, ?, ?, ?, ?)",
                        (item.get("id"), item.get("company", ""), item.get("query", ""), item.get("timestamp", ""), json.dumps(item.get("result", {}), ensure_ascii=False))
                    )
        except Exception as e:
            logger.error(f"Failed to migrate reputation_history.json: {e}")
            
    # 2. Mentions
    men_file = os.path.join(DATA_DIR, "mentions_history.json")
    if os.path.exists(men_file):
        try:
            with open(men_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    cursor.execute(
                        "INSERT OR IGNORE INTO mentions_history (id, company, query, timestamp, result) VALUES (?, ?, ?, ?, ?)",
                        (item.get("id"), item.get("company", ""), item.get("query", ""), item.get("timestamp", ""), json.dumps(item.get("result", {}), ensure_ascii=False))
                    )
        except Exception as e:
            logger.error(f"Failed to migrate mentions_history.json: {e}")
            
    # 3. Negative
    neg_file = os.path.join(DATA_DIR, "negative_history.json")
    if os.path.exists(neg_file):
        try:
            with open(neg_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    cursor.execute(
                        "INSERT OR IGNORE INTO negative_history (id, query, timestamp, result) VALUES (?, ?, ?, ?)",
                        (item.get("id"), item.get("query", ""), item.get("timestamp", ""), json.dumps(item.get("result", {}), ensure_ascii=False))
                    )
        except Exception as e:
            logger.error(f"Failed to migrate negative_history.json: {e}")
            
    # 4. Competitors
    comp_file = os.path.join(DATA_DIR, "competitors_history.json")
    if os.path.exists(comp_file):
        try:
            with open(comp_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    cursor.execute(
                        "INSERT OR IGNORE INTO competitors_history (id, query, timestamp, result) VALUES (?, ?, ?, ?)",
                        (item.get("id"), item.get("query", ""), item.get("timestamp", ""), json.dumps(item.get("result", {}), ensure_ascii=False))
                    )
        except Exception as e:
            logger.error(f"Failed to migrate competitors_history.json: {e}")
            
    # 5. Projects
    proj_file = os.path.join(DATA_DIR, "projects.json")
    if os.path.exists(proj_file):
        try:
            with open(proj_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    cursor.execute(
                        "INSERT OR IGNORE INTO projects (id, name, links, company, direction, city, address, website, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            item.get("id"),
                            item.get("name", ""),
                            json.dumps(item.get("links", []), ensure_ascii=False),
                            item.get("company"),
                            item.get("direction"),
                            item.get("city"),
                            item.get("address"),
                            item.get("website"),
                            item.get("created_at", "")
                        )
                    )
        except Exception as e:
            logger.error(f"Failed to migrate projects.json: {e}")

    conn.commit()
    conn.close()
    
    # Mark as migrated
    with open(migrated_flag, "w") as f:
        f.write("migrated")
    logger.info("JSON to SQLite migration completed.")
