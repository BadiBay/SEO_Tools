import json
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from loguru import logger
from app.services.database import get_db_connection

def save_mentions_search_result(company: str, query: str, search_result: Dict[str, Any]):
    entry_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO mentions_history (id, company, query, timestamp, result) VALUES (?, ?, ?, ?, ?)",
        (entry_id, company, query, timestamp, json.dumps(search_result, ensure_ascii=False))
    )
    conn.commit()
    conn.close()
    
    logger.info(f"Saved mentions search history for '{company}' (id: {entry_id})")
    
    return {
        "id": entry_id,
        "company": company,
        "query": query,
        "timestamp": timestamp,
        "result": search_result
    }

def get_mentions_history(company: Optional[str] = None) -> List[dict]:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if company:
        cursor.execute("SELECT * FROM mentions_history WHERE company LIKE ? ORDER BY timestamp DESC", (f"%{company}%",))
    else:
        cursor.execute("SELECT * FROM mentions_history ORDER BY timestamp DESC")
        
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

def delete_mentions_history_item(item_id: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM mentions_history WHERE id = ?", (item_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    if deleted:
        logger.info(f"Deleted mentions history item (id: {item_id})")
        
    return deleted
