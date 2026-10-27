import json
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from loguru import logger
from app.services.database import get_db_connection

def save_negative_search_result(query: str, search_result: Dict[str, Any]):
    entry_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO negative_history (id, query, timestamp, result) VALUES (?, ?, ?, ?)",
        (entry_id, query, timestamp, json.dumps(search_result, ensure_ascii=False))
    )
    conn.commit()
    conn.close()
    
    logger.info(f"Saved negative search history (id: {entry_id})")
    
    return {
        "id": entry_id,
        "query": query,
        "timestamp": timestamp,
        "result": search_result
    }

def get_negative_history() -> List[dict]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM negative_history ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    conn.close()
    
    data = []
    for row in rows:
        data.append({
            "id": row["id"],
            "query": row["query"],
            "timestamp": row["timestamp"],
            "result": json.loads(row["result"])
        })
        
    return data

def delete_history_item(item_id: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM negative_history WHERE id = ?", (item_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    if deleted:
        logger.info(f"Deleted negative history item (id: {item_id})")
        
    return deleted

def update_history_item(item_id: str, new_result: Dict[str, Any]) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM negative_history WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False
        
    cursor.execute(
        "UPDATE negative_history SET result = ? WHERE id = ?",
        (json.dumps(new_result, ensure_ascii=False), item_id)
    )
    conn.commit()
    conn.close()
    
    logger.info(f"Updated negative history item (id: {item_id})")
    return True
