import json
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from loguru import logger
from app.services.database import get_db_connection

def save_reputation_search_result(company: str, query: str, search_result: Dict[str, Any]):
    """
    Сохраняет результат поиска репутации в SQLite.
    """
    entry_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO reputation_history (id, company, query, timestamp, result) VALUES (?, ?, ?, ?, ?)",
        (entry_id, company, query, timestamp, json.dumps(search_result, ensure_ascii=False))
    )
    conn.commit()
    conn.close()
    
    logger.info(f"Saved reputation search history for '{company}' (id: {entry_id})")
    
    return {
        "id": entry_id,
        "company": company,
        "query": query,
        "timestamp": timestamp,
        "result": search_result
    }

def get_reputation_history(company: Optional[str] = None) -> List[dict]:
    """
    Возвращает историю поиска репутации из SQLite.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if company:
        cursor.execute("SELECT * FROM reputation_history WHERE company LIKE ? ORDER BY timestamp DESC", (f"%{company}%",))
    else:
        cursor.execute("SELECT * FROM reputation_history ORDER BY timestamp DESC")
        
    rows = cursor.fetchall()
    conn.close()
    
    data = []
    for row in rows:
        data.append({
            "id": row["id"],
            "company": row["company"],
            "query": row["query"],
            "timestamp": row["timestamp"],
            "result": json.loads(row["result"])
        })
        
    return data

def delete_history_item(item_id: str) -> bool:
    """
    Удаляет отчет из истории по его ID в SQLite.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM reputation_history WHERE id = ?", (item_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    if deleted:
        logger.info(f"Deleted reputation history item (id: {item_id})")
        
    return deleted

def update_history_item(item_id: str, new_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Обновляет результаты (например, после ручного добавления оценки) в истории (SQLite).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM reputation_history WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
        
    cursor.execute(
        "UPDATE reputation_history SET result = ? WHERE id = ?",
        (json.dumps(new_result, ensure_ascii=False), item_id)
    )
    conn.commit()
    conn.close()
    
    logger.info(f"Updated reputation history item (id: {item_id})")
    
    return {
        "id": row["id"],
        "company": row["company"],
        "query": row["query"],
        "timestamp": row["timestamp"],
        "result": new_result
    }
