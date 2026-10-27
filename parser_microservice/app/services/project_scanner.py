import asyncio
from datetime import datetime, timedelta, timezone
from loguru import logger
from app.schemas.projects import ProjectModel, ProjectScanResponse, ScanResultItem
from app.schemas.scraper import YandexMapCardRequest, ReviewMonitorRequest
from app.services.yandex_maps import parse_yandex_map_card
from app.services.reviews_monitor import parse_reviews_monitor

async def scan_project_links(project: ProjectModel) -> ProjectScanResponse:
    """
    Сканирование всех ссылок проекта.
    В данном случае для Яндекс Карт мы объединяем базовый парсинг (рейтинг)
    и мониторинг (последние отзывы).
    В будущем можно добавить парсеры для 2gis.ru, Google Maps и т.д.
    """
    logger.info(f"Начало сканирования проекта '{project.name}' (ссылок: {len(project.links)})")
    
    results = []
    
    # Дата для мониторинга новых отзывов: например, за последний месяц (30 дней)
    last_check_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    
    for url in project.links:
        logger.info(f"Сканирование URL: {url}")
        
        item_result = ScanResultItem(url=url, status="pending")
        
        # Определяем платформу по URL
        if "yandex.ru" in url or "yandex.com" in url or "ya.ru" in url:
            try:
                # 1. Получаем базовую статистику (рейтинг, кол-во отзывов)
                logger.debug(f"Получение базовой статистики для {url}")
                basic_req = YandexMapCardRequest(url=url)
                basic_res = await parse_yandex_map_card(basic_req)
                
                if basic_res.status == "success":
                    item_result.rating = basic_res.rating
                    item_result.reviews_count = basic_res.reviews_count
                    item_result.status = "success"
                else:
                    item_result.status = "error"
                    item_result.error_message = basic_res.error_message
                    
                # 2. Получаем последние отзывы (мониторинг)
                logger.debug(f"Получение последних отзывов для {url}")
                monitor_req = ReviewMonitorRequest(url=url, last_check_date=last_check_date)
                monitor_res = await parse_reviews_monitor(monitor_req)
                
                if monitor_res.status == "success":
                    item_result.new_reviews = [r.model_dump() for r in monitor_res.new_reviews[:5]]
                    
            except Exception as e:
                logger.exception(f"Ошибка при сканировании Яндекса {url}")
                item_result.status = "error"
                item_result.error_message = str(e)
                
        elif "2gis.ru" in url or "2gis.com" in url:
            from app.services.twogis_parser import parse_twogis_map_card, parse_twogis_reviews_monitor
            try:
                # 1. Получаем базовую статистику (рейтинг, кол-во отзывов)
                logger.debug(f"Получение базовой статистики 2GIS для {url}")
                basic_req = YandexMapCardRequest(url=url) # используем ту же схему запроса
                basic_res = await parse_twogis_map_card(basic_req)
                
                if basic_res.status == "success":
                    item_result.rating = basic_res.rating
                    item_result.reviews_count = basic_res.reviews_count
                    item_result.status = "success"
                else:
                    item_result.status = "error"
                    item_result.error_message = basic_res.error_message
                    
                # 2. Получаем последние отзывы (мониторинг)
                logger.debug(f"Получение последних отзывов 2GIS для {url}")
                monitor_req = ReviewMonitorRequest(url=url, last_check_date=last_check_date)
                monitor_res = await parse_twogis_reviews_monitor(monitor_req)
                
                if monitor_res.status == "success":
                    item_result.new_reviews = [r.model_dump() for r in monitor_res.new_reviews[:5]]
                    
            except Exception as e:
                logger.exception(f"Ошибка при сканировании 2GIS {url}")
                item_result.status = "error"
                item_result.error_message = str(e)
        else:
            item_result.status = "error"
            item_result.error_message = "Платформа не поддерживается"
            
        results.append(item_result)
        
    logger.success(f"Сканирование проекта '{project.name}' завершено.")
    return ProjectScanResponse(
        project_id=project.id,
        scan_date=datetime.now(timezone.utc).isoformat(),
        results=results
    )
