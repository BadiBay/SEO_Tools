import json
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from loguru import logger
from app.services.database import get_db_connection

import os
from app.services.database import DATA_DIR

def get_all_projects() -> List[dict]:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM projects ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        
        data = []
        for row in rows:
            data.append({
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
            
        return data
    except Exception as e:
        logger.error(f"Error fetching projects from SQLite: {e}")
        proj_file = os.path.join(DATA_DIR, "projects.json")
        if os.path.exists(proj_file):
            try:
                with open(proj_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as fe:
                logger.error(f"Fallback reading projects.json failed: {fe}")
        return []

def get_project(project_id: str) -> Optional[dict]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "id": row["id"],
            "name": row["name"],
            "links": json.loads(row["links"]) if row["links"] else [],
            "company": row["company"],
            "direction": row["direction"],
            "city": row["city"],
            "address": row["address"],
            "website": row["website"],
            "created_at": row["created_at"]
        }
    return None

def create_project(project_data: Any) -> dict:
    project_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat() + "Z"
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # If it's a Pydantic model
    if hasattr(project_data, 'model_dump'):
        data = project_data.model_dump()
    elif hasattr(project_data, 'dict'):
        data = project_data.dict()
    else:
        data = project_data

    cursor.execute(
        "INSERT INTO projects (id, name, links, company, direction, city, address, website, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            project_id,
            data.get("name", ""),
            json.dumps(data.get("links", []), ensure_ascii=False),
            data.get("company"),
            data.get("direction"),
            data.get("city"),
            data.get("address"),
            data.get("website"),
            created_at
        )
    )
    conn.commit()
    conn.close()
    
    logger.info(f"Created project '{data.get('name')}' (id: {project_id})")
    
    return {
        "id": project_id,
        "name": data.get("name", ""),
        "links": data.get("links", []),
        "company": data.get("company"),
        "direction": data.get("direction"),
        "city": data.get("city"),
        "address": data.get("address"),
        "website": data.get("website"),
        "created_at": created_at
    }

def update_project(project_id: str, updates: dict) -> Optional[dict]:
    proj = get_project(project_id)
    if not proj:
        return None
        
    for k, v in updates.items():
        proj[k] = v
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE projects SET name = ?, links = ?, company = ?, direction = ?, city = ?, address = ?, website = ? WHERE id = ?",
        (
            proj.get("name"),
            json.dumps(proj.get("links", []), ensure_ascii=False),
            proj.get("company"),
            proj.get("direction"),
            proj.get("city"),
            proj.get("address"),
            proj.get("website"),
            project_id
        )
    )
    conn.commit()
    conn.close()
    
    logger.info(f"Updated project (id: {project_id})")
    return proj

def delete_project(project_id: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    if deleted:
        logger.info(f"Deleted project (id: {project_id})")
        
    return deleted
