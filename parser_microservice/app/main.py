from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import List
from app.schemas.scraper import (
    YandexMapCardRequest, YandexMapCardResponse,
    ReviewMonitorRequest, ReviewMonitorResponse,
    CompetitorAnalysisRequest, CompetitorAnalysisResponse
)
from app.schemas.projects import ProjectModel, ProjectCreate, ProjectUpdate, ProjectScanResponse
from app.services.yandex_maps import parse_yandex_map_card
from app.services.reviews_monitor import parse_reviews_monitor
from app.services.competitors_analysis import parse_competitors_analysis
from app.services.projects_db import get_all_projects, get_project, create_project, update_project, delete_project
from app.services.project_scanner import scan_project_links
from app.services.database import init_db
import logging
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up parser microservice...")
    init_db()
    yield
    logger.info("Shutting down parser microservice...")

app = FastAPI(
    title="SEO Scraper Microservice",
    description="Микросервис для парсинга геосервисов и поисковой выдачи",
    version="1.0.0",
    lifespan=lifespan
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
async def serve_frontend():
    return FileResponse("app/static/index.html")

# --- SCRAPER ENDPOINTS ---

@app.post("/api/v1/parse/yandex-map", response_model=YandexMapCardResponse)
async def parse_yandex_map_endpoint(request: YandexMapCardRequest):
    result = await parse_yandex_map_card(request)
    return result

@app.post("/api/v1/parse/reviews-monitor", response_model=ReviewMonitorResponse)
async def parse_reviews_monitor_endpoint(request: ReviewMonitorRequest):
    result = await parse_reviews_monitor(request)
    return result

from app.services.competitors_history_db import save_competitors_search_result, get_competitors_history, delete_competitors_history_item
from app.services.google_sheets import append_competitors_results_to_sheet

@app.post("/api/v1/parse/competitors", response_model=CompetitorAnalysisResponse)
async def parse_competitors_endpoint(request: CompetitorAnalysisRequest):
    result = await parse_competitors_analysis(request)
    if result.status == "success":
        save_competitors_search_result(request.query, request.lat, request.lon, result.model_dump())
        append_competitors_results_to_sheet(request.query, [c.model_dump() for c in result.competitors])
    return result

# --- 2GIS ENDPOINTS ---

from app.services.twogis_parser import (
    parse_twogis_map_card,
    parse_twogis_reviews_monitor,
    parse_twogis_competitors
)

@app.post("/api/v1/parse/twogis-map", response_model=YandexMapCardResponse)
async def parse_twogis_map_endpoint(request: YandexMapCardRequest):
    result = await parse_twogis_map_card(request)
    return result

@app.post("/api/v1/parse/twogis-reviews-monitor", response_model=ReviewMonitorResponse)
async def parse_twogis_reviews_monitor_endpoint(request: ReviewMonitorRequest):
    result = await parse_twogis_reviews_monitor(request)
    return result

@app.post("/api/v1/parse/twogis-competitors", response_model=CompetitorAnalysisResponse)
async def parse_twogis_competitors_endpoint(request: CompetitorAnalysisRequest):
    result = await parse_twogis_competitors(request)
    if result.status == "success":
        save_competitors_search_result(request.query, request.lat, request.lon, result.model_dump())
        append_competitors_results_to_sheet(request.query, [c.model_dump() for c in result.competitors])
    return result

# --- PROJECTS ENDPOINTS ---

@app.get("/api/v1/projects", response_model=List[ProjectModel])
async def read_projects():
    return get_all_projects()

@app.post("/api/v1/projects", response_model=ProjectModel)
async def create_new_project(project_in: ProjectCreate):
    return create_project(project_in)

@app.put("/api/v1/projects/{project_id}", response_model=ProjectModel)
async def update_existing_project(project_id: str, project_in: ProjectUpdate):
    proj = update_project(project_id, project_in.model_dump(exclude_unset=True))
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return proj

@app.delete("/api/v1/projects/{project_id}")
async def delete_existing_project(project_id: str):
    success = delete_project(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"status": "success", "message": "Project deleted"}

@app.post("/api/v1/projects/{project_id}/scan", response_model=ProjectScanResponse)
async def scan_project_endpoint(project_id: str):
    proj = get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    project_model = ProjectModel(**proj)
    result = await scan_project_links(project_model)
    return result

# --- REPUTATION SEARCH ENDPOINTS ---
from app.schemas.scraper import ReputationSearchRequest, ReputationSearchResponse
from app.services.reputation_search import search_reputation

from fastapi.responses import StreamingResponse
import json

@app.post("/api/v1/reputation/search")
async def search_reputation_endpoint(request: ReputationSearchRequest):
    async def generate():
        async for update in search_reputation(request):
            yield json.dumps(update) + "\n"
            
    return StreamingResponse(generate(), media_type="application/x-ndjson")

from typing import Optional
from app.services.reputation_history_db import get_reputation_history, delete_history_item, update_history_item

@app.get("/api/v1/reputation/history")
async def get_reputation_history_endpoint(company: Optional[str] = None):
    return get_reputation_history(company)

@app.delete("/api/v1/reputation/history/{item_id}")
async def delete_reputation_history_endpoint(item_id: str):
    success = delete_history_item(item_id)
    if not success:
        raise HTTPException(status_code=404, detail="History item not found")
    return {"status": "success", "message": "History item deleted"}

from typing import Dict, Any

from fastapi import BackgroundTasks
from app.services.google_sheets import append_reputation_results_to_sheet

@app.put("/api/v1/reputation/history/{item_id}")
async def update_reputation_history_endpoint(item_id: str, new_result: Dict[str, Any], background_tasks: BackgroundTasks):
    item = update_history_item(item_id, new_result)
    if not item:
        raise HTTPException(status_code=404, detail="History item not found")
        
    # Синхронизация с Google Sheets в фоне
    company = item.get("company", "")
    query = item.get("query", "")
    background_tasks.add_task(append_reputation_results_to_sheet, company, query, item.get("result", {}))
    
    return {"status": "success", "message": "History item updated and synced to Google Sheets"}

# --- COMPETITORS HISTORY ENDPOINTS ---

@app.get("/api/v1/competitors/history")
async def get_competitors_history_endpoint(query: Optional[str] = None):
    return get_competitors_history(query)

@app.delete("/api/v1/competitors/history/{item_id}")
async def delete_competitors_history_endpoint(item_id: str):
    success = delete_competitors_history_item(item_id)
    if not success:
        raise HTTPException(status_code=404, detail="Competitors history item not found")
    return {"status": "success", "message": "Competitors history item deleted"}

# --- MENTIONS SEARCH ENDPOINTS ---
from app.schemas.scraper import MentionsSearchRequest
from app.services.mentions_search import search_mentions
from app.services.mentions_history_db import get_mentions_history, delete_mentions_history_item

@app.post("/api/v1/mentions/search")
async def search_mentions_endpoint(request: MentionsSearchRequest):
    async def generate():
        async for update in search_mentions(request):
            yield json.dumps(update) + "\n"
            
    return StreamingResponse(generate(), media_type="application/x-ndjson")

@app.get("/api/v1/mentions/history")
async def get_mentions_history_endpoint(company: Optional[str] = None):
    return get_mentions_history(company)

@app.delete("/api/v1/mentions/history/{item_id}")
async def delete_mentions_history_endpoint(item_id: str):
    success = delete_mentions_history_item(item_id)
    if not success:
        raise HTTPException(status_code=404, detail="Mentions history item not found")
    return {"status": "success", "message": "Mentions history item deleted"}


# --- NEGATIVE SEARCH ENDPOINTS ---
from app.schemas.scraper import NegativeSearchRequest
from app.services.negative_search import search_negative
from app.services.negative_history_db import get_negative_history, delete_history_item as delete_negative_history_item, update_history_item as update_negative_history_item

@app.post("/api/v1/negative/search")
async def search_negative_endpoint(request: NegativeSearchRequest):
    async def generate():
        async for update in search_negative(request):
            yield json.dumps(update) + "\n"
            
    return StreamingResponse(generate(), media_type="application/x-ndjson")

@app.get("/api/v1/negative/history")
async def get_negative_history_endpoint():
    return get_negative_history()

@app.delete("/api/v1/negative/history/{item_id}")
async def delete_negative_history_endpoint(item_id: str):
    success = delete_negative_history_item(item_id)
    if not success:
        raise HTTPException(status_code=404, detail="Negative history item not found")
    return {"status": "success", "message": "Negative history item deleted"}

@app.put("/api/v1/negative/history/{item_id}")
async def update_negative_history_endpoint(item_id: str, new_result: Dict[str, Any]):
    success = update_negative_history_item(item_id, new_result)
    if not success:
        raise HTTPException(status_code=404, detail="Negative history item not found")
    return {"status": "success", "message": "Negative history item updated"}
