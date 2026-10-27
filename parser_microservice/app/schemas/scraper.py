from pydantic import BaseModel, HttpUrl, Field
from typing import Optional

class YandexMapCardRequest(BaseModel):
    """Модель входных данных для парсинга карточки Яндекс Карт."""
    url: HttpUrl = Field(..., description="Прямой URL карточки организации на Яндекс Картах")


class YandexMapCardResponse(BaseModel):
    """Модель выходных данных после парсинга карточки."""
    rating: Optional[float] = Field(None, description="Рейтинг организации")
    reviews_count: Optional[int] = Field(None, description="Количество оценок/отзывов")
    status: str = Field(..., description="Статус выполнения парсинга (success, error, captcha)")
    error_message: Optional[str] = Field(None, description="Сообщение об ошибке, если статус error или captcha")


class ReviewModel(BaseModel):
    """Модель одного отзыва."""
    author: Optional[str] = Field(None, description="Имя автора отзыва")
    text: Optional[str] = Field(None, description="Текст отзыва")
    rating: Optional[float] = Field(None, description="Оценка пользователя")
    date_parsed: Optional[str] = Field(None, description="Дата отзыва в формате ISO 8601")
    date_raw: Optional[str] = Field(None, description="Оригинальная строка с датой")
    has_reply: bool = Field(False, description="Есть ли официальный ответ от организации")


class ScraperTaskResponse(BaseModel):
    """Модель ответа при запуске фоновой задачи."""
    task_id: str = Field(..., description="ID запущенной celery-задачи")
    status: str = Field(..., description="Статус: processing")


class ReputationSearchRequest(BaseModel):
    """Модель запроса для поиска упоминаний."""
    company: str = Field(..., description="Название компании")
    direction: str = Field(..., description="Основное направление")
    city: str = Field(..., description="Город")
    address: Optional[str] = Field(None, description="Дополнительный адрес или улица")
    website: Optional[str] = Field(None, description="Сайт компании для уточнения поиска")


class ReputationSiteResult(BaseModel):
    """Модель одного найденного сайта-отзовика."""
    url: str = Field(..., description="Ссылка на страницу с отзывами")
    domain: str = Field(..., description="Домен сайта-отзовика")
    rating: Optional[float] = Field(None, description="Найденный рейтинг (AggregateRating)")
    reviews_count: Optional[int] = Field(None, description="Найденное количество отзывов")
    previous_rating: Optional[float] = Field(None, description="Рейтинг при прошлой проверке")
    previous_reviews_count: Optional[int] = Field(None, description="Количество отзывов при прошлой проверке")
    rating_change: Optional[float] = Field(None, description="Изменение рейтинга")
    reviews_count_change: Optional[int] = Field(None, description="Изменение количества отзывов")
    screenshot_url: Optional[str] = Field(None, description="URL сохраненного скриншота")
    status: str = Field(..., description="Статус парсинга: success или error")


class ReputationSearchResponse(BaseModel):
    """Модель ответа с результатами поиска репутации."""
    history_id: Optional[str] = Field(None, description="ID записи в истории")
    status: str = Field(..., description="Статус выполнения (success, error)")
    website_title: str = Field(..., description="Извлеченный заголовок сайта")
    search_query: str = Field(..., description="Сформированный поисковый запрос")
    sites: list[ReputationSiteResult] = Field(default_factory=list, description="Список площадок с отзывами")
    error_message: Optional[str] = Field(None, description="Сообщение об ошибке")


class ReviewMonitorRequest(BaseModel):
    """Модель запроса на мониторинг отзывов."""
    url: HttpUrl = Field(..., description="Прямой URL карточки организации")
    last_check_date: str = Field(..., description="Дата последней проверки (ISO 8601). Отзывы старше или равные этой дате не собираются.")


class ReviewMonitorResponse(BaseModel):
    """Модель ответа мониторинга отзывов."""
    status: str = Field(..., description="Статус выполнения (success, error, captcha)")
    new_reviews: list[ReviewModel] = Field(default_factory=list, description="Список собранных новых отзывов")
    error_message: Optional[str] = Field(None, description="Сообщение об ошибке")


class CompetitorReview(BaseModel):
    """Модель отзыва конкурента."""
    text: Optional[str] = Field(None, description="Текст отзыва")
    rating: Optional[float] = Field(None, description="Оценка")
    type: str = Field(..., description="Тип отзыва: positive или negative")
    has_reply: bool = Field(False, description="Есть ли официальный ответ")


class CompetitorModel(BaseModel):
    """Модель конкурента."""
    name: Optional[str] = Field(None, description="Название конкурента")
    url: Optional[str] = Field(None, description="Ссылка на геосервис")
    rating: Optional[float] = Field(None, description="Рейтинг конкурента")
    reviews_count: Optional[int] = Field(None, description="Количество оценок")
    is_ad: bool = Field(False, description="Является ли размещение платным/приоритетным")
    ad_type: Optional[str] = Field(None, description="Тип рекламы (premium_block, branded_pin, etc)")
    top_positive_reviews: list[CompetitorReview] = Field(default_factory=list, description="Топ позитивных отзывов")
    top_negative_reviews: list[CompetitorReview] = Field(default_factory=list, description="Топ негативных отзывов")


class CompetitorAnalysisRequest(BaseModel):
    """Запрос на конкурентный анализ."""
    url: Optional[str] = Field(None, description="Ссылка на организацию (для авто-определения координат)")
    lat: Optional[float] = Field(None, description="Широта (если нет url)")
    lon: Optional[float] = Field(None, description="Долгота (если нет url)")
    radius: int = Field(default=1000, description="Радиус поиска в метрах")
    query: str = Field(..., description="Поисковый запрос (например, 'кофейня')")
    limit: int = Field(default=3, description="Количество конкурентов для анализа")


class CompetitorAnalysisResponse(BaseModel):
    """Ответ на конкурентный анализ."""
    status: str = Field(..., description="Статус выполнения (success, error, captcha)")
    competitors: list[CompetitorModel] = Field(default_factory=list, description="Список конкурентов")
    error_message: Optional[str] = Field(None, description="Сообщение об ошибке")


class MentionsSearchRequest(BaseModel):
    """Запрос для поиска любых упоминаний."""
    company: str = Field(..., description="Название компании")
    website: str = Field(..., description="Ссылка на сайт компании (например, domain.com или https://domain.com)")
    city: Optional[str] = Field(None, description="Город (опционально)")


class MentionSiteResult(BaseModel):
    """Модель одного найденного сайта с упоминанием."""
    url: str = Field(..., description="Ссылка на найденную страницу")
    domain: str = Field(..., description="Домен найденного сайта")
    title: Optional[str] = Field(None, description="Заголовок страницы")
    snippet: Optional[str] = Field(None, description="Сниппет из поисковика")
    is_link_present: bool = Field(False, description="Присутствует ли ссылка на искомый сайт на странице")
    status: str = Field(..., description="Статус парсинга: success или error")


class MentionsSearchResponse(BaseModel):
    """Модель ответа с результатами поиска упоминаний."""
    status: str = Field(..., description="Статус выполнения (success, error)")
    search_query: str = Field(..., description="Сформированный поисковый запрос")
    sites: list[MentionSiteResult] = Field(default_factory=list, description="Список площадок с упоминаниями")
    error_message: Optional[str] = Field(None, description="Сообщение об ошибке")


class NegativeSearchRequest(BaseModel):
    """Модель запроса для поиска негатива."""
    queries: list[str] = Field(..., description="Список поисковых запросов пользователя (кластер)")


class NegativeSiteResult(BaseModel):
    """Модель одного найденного сайта при поиске негатива."""
    url: str = Field(..., description="Ссылка на найденную страницу")
    domain: str = Field(..., description="Домен найденного сайта")
    negative_count: Optional[int] = Field(None, description="Количество негативных отзывов/оценок")
    status: str = Field(..., description="Статус парсинга: success или error")


class NegativeSearchResponse(BaseModel):
    """Модель ответа с результатами поиска негатива."""
    history_id: Optional[str] = Field(None, description="ID записи в истории")
    status: str = Field(..., description="Статус выполнения (success, error)")
    search_query: str = Field(..., description="Использованный поисковый запрос")
    sites: list[NegativeSiteResult] = Field(default_factory=list, description="Список площадок с негативом")
    error_message: Optional[str] = Field(None, description="Сообщение об ошибке")
