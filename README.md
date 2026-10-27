# SEOTools — Монорепозиторий SEO-инструментов

> Набор из двух независимых платформ для автоматизации SEO-процессов, управления репутацией и анализа гео-рынков.

---

## Содержание

- [Обзор монорепозитория](#обзор-монорепозитория)
- [Проект 1 — AutoSEO](#проект-1--autoseo)
  - [Обзор](#обзор-autoseo)
  - [Архитектура](#архитектура-autoseo)
  - [Модули](#модули-autoseo)
  - [Стек технологий](#стек-autoseo)
  - [Быстрый старт AutoSEO](#быстрый-старт-autoseo)
  - [Конфигурация AutoSEO](#конфигурация-autoseo)
  - [Структура проекта AutoSEO](#структура-autoseo)
  - [API AutoSEO](#api-autoseo)
  - [Интеграции AutoSEO](#интеграции-autoseo)
  - [Фоновые задачи AutoSEO](#фоновые-задачи-autoseo)
  - [Разработка AutoSEO](#разработка-autoseo)
- [Проект 2 — Parser Microservice](#проект-2--parser-microservice)
  - [Обзор](#обзор-parser)
  - [Архитектура](#архитектура-parser)
  - [Модули парсера](#модули-парсера)
  - [Стек технологий](#стек-parser)
  - [Быстрый старт Parser](#быстрый-старт-parser)
  - [Конфигурация Parser](#конфигурация-parser)
  - [Структура проекта Parser](#структура-parser)
  - [API Parser](#api-parser)
  - [Интеграции Parser](#интеграции-parser)
  - [Разработка Parser](#разработка-parser)
- [Связь между проектами](#связь-между-проектами)

---

## Обзор монорепозитория

```
SEOTools/
├── autoSEO/             # Полноценная платформа: ссылки, конкуренты, alt-теги
└── parser_microservice/ # Микросервис: парсинг геосервисов, репутация, упоминания
```

| Проект | Назначение | Стек |
|--------|-----------|------|
| **AutoSEO** | Управление SEO: бесплатные/платные ссылки, анализ конкурентов, генерация alt-тегов | FastAPI + React + PostgreSQL + Celery |
| **Parser Microservice** | Парсинг Яндекс.Карт и 2ГИС, мониторинг репутации, поиск упоминаний и негатива | FastAPI + Playwright + SQLite + Google Sheets |

---

---

# Проект 1 — AutoSEO

> **Платформа автоматизации SEO-процессов:** анализ конкурентов, управление бесплатным и платным линкбилдингом, генерация alt-тегов с помощью LLM.

## Обзор AutoSEO

AutoSEO — внутренняя платформа, организованная вокруг **Проектов** (сайтов). Для каждого проекта доступны четыре независимых модуля:

| Модуль | Назначение |
|--------|-----------|
| 🔍 **Анализ конкурентов** | Автоматический парсинг SERP, сбор метрик (Keys.so, Semrush), AI-классификация конкурентов |
| 🔗 **Бесплатные ссылки** | База площадок-доноров, размещение ссылок, мониторинг живучести и индексации |
| 💰 **Платные ссылки** | Управление аутричем, генерация статей через LLM, контроль публикации и индексации |
| 🖼️ **Alt-теги** | Пакетная генерация alt-тегов для изображений через LLM с экспортом в Google Sheets |

---

## Архитектура AutoSEO

```
┌─────────────────────────────────────────────────────────┐
│                        Nginx :80                        │
│          (reverse proxy + WebSocket upgrade)            │
└──────────────┬──────────────────────┬───────────────────┘
               │ /api/*, /ws/         │ /*
               ▼                      ▼
┌──────────────────────┐   ┌──────────────────────────────┐
│   FastAPI :8000      │   │   React + Vite :5173          │
│   (async REST + WS)  │   │   (TypeScript, React Router)  │
└──────┬───────────────┘   └──────────────────────────────┘
       │
       ├──► PostgreSQL :5432  (основная БД, SQLAlchemy async)
       ├──► Redis :6379        (кэш, Celery broker/backend)
       ├──► MinIO :9000/:9001  (S3-совместимое хранилище медиа)
       │
       └──► Celery Worker      (4 воркера: default, competitors, links, alt_tags)
            Celery Beat         (планировщик регулярных задач)
```

Все сервисы запускаются через **Docker Compose** и общаются по внутренней Docker-сети.

---

## Модули AutoSEO

### 1. Анализ конкурентов

**Pipeline:** `CompetitorPipeline` (`backend/app/services/competitor_pipeline.py`)

1. Пользователь указывает маркерные запросы и приоритетные направления бизнеса.
2. Парсинг SERP (Google / Yandex) — определяет домены конкурентов.
3. Сбор метрик для каждого домена:
   - **Keys.so** — трафик, видимость, позиции в ТОП-10/50, семантика, PPC-бюджет.
   - **Semrush** — Domain Rating, обратные ссылки, тренд ссылочного профиля.
   - **WHOIS** — возраст домена.
   - **Vision AI (Gemini)** — скриншот графика видимости → тренд (рост/спад/стагнация).
4. AI-классификация (LLM): прямой или косвенный конкурент + обоснование.
5. Анализ УТП и структуры сайта (Perplexity / Gemini).
6. Результаты сохраняются в `CompetitorReport` — доступны в UI с фильтрацией и экспортом.

**Статусы пайплайна:** `pending → running → done / failed`

---

### 2. Бесплатные ссылки

**Ключевые сущности:**
- `DonorPlatform` — справочник площадок-доноров (тип: каталог, форум, профиль, статья).
- `FreeLink` — размещённая ссылка с таргетом, анкором, промо-текстом и алиасом email.

**Статусы ссылки:** `pending → placed → verified → dead / reindexing`

**Мониторинг (Celery Beat):**
- Ежемесячная проверка живучести (`check_free_links_alive`) — HTTP-запрос к `placed_url`.
- Проверка индексации (`check_free_links_indexation`) — отправка в Google Indexing API.

---

### 3. Платные ссылки

**Ключевые сущности:**
- `KeywordCluster` — кластер ключевых слов с LSI и вариантами анкоров.
- `PaidLink` — статья на доноре с полным жизненным циклом.
- `UsedDonor` — анти-дубль система (гарантирует уникальность доноров на проект).

**Генерация через LLM:**
- Заголовок, HTML-текст статьи, мета-данные.
- Инструкции для вебмастера.
- Проверки: тональность, структура.

**Статусы:** `draft → review → submitted → published → indexed / rejected`

**Мониторинг:** `check_paid_links_indexation` — проверка HTTP-доступности страницы донора с уведомлением при сбое.

---

### 4. Alt-теги

**Пакетная генерация:**
- Загрузка изображений (через URL или файл).
- LLM генерирует осмысленные alt-теги с учётом контекста страницы.
- Результаты группируются в **батчи** (`AltTagBatch`).
- Экспорт в **Google Sheets** для согласования и внедрения.

---

## Стек AutoSEO

### Backend

| Компонент | Технология |
|-----------|-----------|
| Web-фреймворк | FastAPI 0.115 + Uvicorn |
| База данных | PostgreSQL 16 + SQLAlchemy 2.0 (async) + Alembic |
| Очередь задач | Celery 5.4 + Redis |
| HTTP-клиент | httpx, aiohttp |
| Web-scraping | BeautifulSoup4, lxml |
| Хранилище медиа | MinIO (S3) + boto3 |
| Уведомления | python-telegram-bot, SMTP |
| Утилиты | Pydantic v2, python-whois, Pillow, openpyxl |

### LLM-провайдеры

| Провайдер | SDK |
|-----------|-----|
| Google Gemini | google-genai |
| OpenAI | openai |
| Anthropic Claude | anthropic |
| Perplexity | httpx (REST) |
| Mock | встроенный (для тестов без API-ключей) |

### Frontend

| Компонент | Технология |
|-----------|-----------|
| UI-фреймворк | React 18 + TypeScript |
| Сборка | Vite |
| Маршрутизация | React Router v6 |
| Стили | Vanilla CSS (кастомные переменные, dark-mode) |

### Инфраструктура

| Компонент | Технология |
|-----------|-----------|
| Контейнеризация | Docker + Docker Compose |
| Reverse Proxy | Nginx (+ WebSocket upgrade) |
| Планировщик | Celery Beat |

---

## Быстрый старт AutoSEO

### Требования

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (или Docker Engine + Compose)
- Git

### 1. Перейти в папку проекта

```bash
cd autoSEO
```

### 2. Настроить переменные окружения

```bash
cp .env.example .env
```

Откройте `.env` и заполните нужные API-ключи. Для базового запуска ничего не нужно — по умолчанию используется `mock` LLM-провайдер.

### 3. Запустить все сервисы

```bash
docker compose up --build
```

После запуска доступно:

| Сервис | URL |
|--------|-----|
| Frontend (React) | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| MinIO Console | http://localhost:9001 |
| Через Nginx | http://localhost:80 |

### 4. Создать первый проект

Откройте http://localhost и создайте проект через интерфейс.

---

## Конфигурация AutoSEO

Все настройки задаются через переменные окружения в файле `.env`. Шаблон — `.env.example`.

### База данных

```env
POSTGRES_USER=autoseo
POSTGRES_PASSWORD=autoseo_secret_change_me
POSTGRES_DB=autoseo
DATABASE_URL=postgresql+asyncpg://autoseo:autoseo_secret_change_me@postgres:5432/autoseo
```

### Redis / Celery

```env
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
```

### MinIO (хранилище)

```env
MINIO_ROOT_USER=autoseo_minio
MINIO_ROOT_PASSWORD=minio_secret_change_me
MINIO_ENDPOINT=minio:9000
MINIO_BUCKET=autoseo-media
```

### LLM-провайдеры

```env
# Выбор активного провайдера: gemini | openai | anthropic | mock
DEFAULT_LLM_PROVIDER=mock

GEMINI_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
PERPLEXITY_API_KEY=
```

> **Совет:** Для тестирования без реальных ключей оставьте `DEFAULT_LLM_PROVIDER=mock`.

### SEO API

```env
KEYS_SO_API_KEY=       # Keys.so — трафик и видимость
SEMRUSH_API_KEY=       # Semrush — ссылочный профиль
```

### SERP-парсинг

```env
# custom (встроенный) | serpapi | serper
SERP_PROVIDER=custom
SERPAPI_KEY=
SERPER_API_KEY=
```

### Google API

```env
# JSON-строка с сервисным аккаунтом (base64 или inline JSON)
GOOGLE_SHEETS_CREDENTIALS_JSON=
GOOGLE_INDEXING_CREDENTIALS_JSON=
```

### Уведомления

```env
# Email (SMTP)
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=

# Telegram
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Webhook
WEBHOOK_URL=
```

### Производительность

```env
DEFAULT_RATE_LIMIT_DELAY=0.7   # задержка между API-запросами (сек)
LLM_BATCH_SIZE=5               # размер батча для LLM
SERP_BATCH_SIZE=10             # размер батча для SERP
```

---

## Структура AutoSEO

```
autoSEO/
├── .env                        # Конфигурация (не коммитить!)
├── .env.example                # Шаблон конфигурации
├── docker-compose.yml          # Оркестрация сервисов
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py             # Точка входа FastAPI
│       ├── config.py           # Настройки (pydantic-settings)
│       ├── database.py         # Подключение к БД, сессии
│       │
│       ├── models/             # SQLAlchemy ORM-модели
│       │   ├── project.py
│       │   ├── competitor.py   # CompetitorReport, MarkerQuery, Competitor
│       │   ├── link.py         # DonorPlatform, FreeLink, KeywordCluster, PaidLink, UsedDonor
│       │   ├── alt_tag.py      # AltTagBatch, AltTagItem
│       │   ├── pipeline.py     # PipelineRun
│       │   ├── notification.py
│       │   └── system_setting.py
│       │
│       ├── api/                # FastAPI роутеры
│       │   ├── projects.py
│       │   ├── competitors.py
│       │   ├── free_links.py
│       │   ├── paid_links.py
│       │   ├── alt_tags.py
│       │   ├── notifications.py
│       │   ├── settings.py
│       │   └── websocket.py    # WebSocket для live-обновлений
│       │
│       ├── services/           # Бизнес-логика (пайплайны)
│       │   ├── competitor_pipeline.py
│       │   ├── paid_link_pipeline.py
│       │   └── pipeline_manager.py
│       │
│       ├── integrations/       # Адаптеры внешних сервисов
│       │   ├── base.py
│       │   ├── web_scraper.py
│       │   ├── indexing_api.py # Google Indexing API
│       │   ├── alias_manager.py
│       │   ├── llm/
│       │   │   ├── factory.py  # Фабрика провайдеров
│       │   │   ├── gemini.py
│       │   │   ├── openai_provider.py
│       │   │   ├── perplexity.py
│       │   │   └── mock.py
│       │   ├── seo/
│       │   │   ├── keys_so.py
│       │   │   ├── semrush.py
│       │   │   └── mock.py
│       │   └── serp/
│       │       └── parser.py
│       │
│       ├── tasks/              # Celery-задачи
│       │   ├── celery_app.py
│       │   ├── scheduled_tasks.py
│       │   ├── competitor_tasks.py
│       │   ├── free_link_tasks.py
│       │   ├── alt_tag_tasks.py
│       │   └── link_tasks.py
│       │
│       └── schemas/            # Pydantic-схемы (request/response)
│
├── frontend/
│   ├── Dockerfile
│   ├── vite.config.ts
│   ├── package.json
│   └── src/
│       ├── App.tsx             # Роутинг и sidebar
│       ├── main.tsx
│       ├── api/
│       │   └── client.ts       # API-клиент
│       ├── pages/
│       │   ├── ProjectsPage.tsx
│       │   ├── ProjectDetailPage.tsx
│       │   ├── AnalysisPage.tsx
│       │   ├── FreeLinksPage.tsx
│       │   ├── FreeLinkDetailPage.tsx
│       │   ├── PaidLinksPage.tsx
│       │   ├── PaidLinkDetailPage.tsx
│       │   ├── AltTagsPage.tsx
│       │   ├── AltTagBatchPage.tsx
│       │   ├── NotificationsPage.tsx
│       │   └── SettingsPage.tsx
│       └── styles/
│
└── nginx/
    └── nginx.conf              # Reverse proxy + WebSocket
```

---

## API AutoSEO

Документация: **http://localhost:8000/docs**

| Группа | Префикс | Описание |
|--------|---------|---------|
| Проекты | `/api/projects` | CRUD проектов |
| Конкуренты | `/api/competitors` | Запуск анализа, просмотр отчётов |
| Бесплатные ссылки | `/api/projects/{id}/free-links` | Управление FreeLink |
| Платные ссылки | `/api/projects/{id}/paid-links` | Управление PaidLink, генерация статей |
| Alt-теги | `/api/projects/{id}/alt-tags` | Батчевая генерация alt-тегов |
| Уведомления | `/api/notifications` | Просмотр и отметка прочитанными |
| Настройки | `/api/settings` | Системные настройки (LLM, API-ключи) |
| Здоровье | `/api/health` | Статус сервиса |
| WebSocket | `/ws/pipeline/{run_id}` | Live-обновления прогресса пайплайна |

---

## Интеграции AutoSEO

### LLM (фабрика провайдеров)

Активный провайдер выбирается через `DEFAULT_LLM_PROVIDER`. Все провайдеры реализуют единый интерфейс.

```
integrations/llm/
├── factory.py        # get_llm_provider() — возвращает нужный адаптер
├── gemini.py         # Google Gemini (включая vision для скриншотов)
├── openai_provider.py
├── perplexity.py     # Для анализа УТП конкурентов
└── mock.py           # Детерминированные ответы для разработки/тестов
```

### SEO API

| Провайдер | Данные |
|-----------|--------|
| **Keys.so** | Трафик, видимость, ТОП-10/50, семантика, PPC-бюджет |
| **Semrush** | Domain Rating, количество и тренд обратных ссылок |

### SERP-парсинг

| Режим | Описание |
|-------|---------|
| `custom` | Встроенный парсер (httpx + BeautifulSoup) |
| `serpapi` | SerpApi.com |
| `serper` | Serper.dev |

### Google API

- **Google Sheets** — экспорт alt-тегов (`gspread` + сервисный аккаунт)
- **Google Indexing API** — принудительная индексация размещённых ссылок

### Уведомления

- **Email** (SMTP)
- **Telegram** (Bot API)
- **Webhook** (HTTP POST)
- **Internal** (в базе данных, отображаются в UI)

---

## Фоновые задачи AutoSEO

Celery-воркер обрабатывает 4 очереди: `default`, `competitors`, `links`, `alt_tags`.

### Регулярные задачи (Celery Beat)

| Задача | Расписание | Описание |
|--------|-----------|---------|
| `check_free_links_alive` | Ежемесячно | Проверка HTTP-доступности бесплатных ссылок |
| `audit_donor_platforms` | Ежемесячно | Аудит базы доноров, выявление закрытых площадок |
| `check_paid_links_indexation` | Регулярно | Проверка доступности страниц платных ссылок |
| `check_free_links_indexation` | Регулярно | Проверка индексации + отправка в Google Indexing API |

### Асинхронные задачи (по запросу)

- Запуск пайплайна анализа конкурентов
- Генерация статьи для платной ссылки
- Генерация alt-тегов (батч)
- Обработка отдельных ссылок

---

## Разработка AutoSEO

### Запуск только Backend (без Docker)

```bash
cd autoSEO/backend

python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Запустить PostgreSQL и Redis отдельно
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=autoseo_secret_change_me -e POSTGRES_USER=autoseo -e POSTGRES_DB=autoseo postgres:16-alpine
docker run -d -p 6379:6379 redis:7-alpine

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# В отдельном терминале — Celery Worker
celery -A app.tasks.celery_app worker --loglevel=info -Q default,competitors,links,alt_tags

# В отдельном терминале — Celery Beat
celery -A app.tasks.celery_app beat --loglevel=info
```

### Запуск только Frontend

```bash
cd autoSEO/frontend
npm install
npm run dev
# -> http://localhost:5173
```

### Миграции БД (Alembic)

```bash
cd autoSEO/backend

# Создать новую миграцию
alembic revision --autogenerate -m "описание изменений"

# Применить миграции
alembic upgrade head

# Откатить последнюю миграцию
alembic downgrade -1
```

> **Примечание:** В текущей конфигурации таблицы создаются автоматически при старте (`Base.metadata.create_all`). Alembic рекомендуется для продакшн-окружений.

### Переключение LLM-провайдера

```env
DEFAULT_LLM_PROVIDER=gemini  # или openai | anthropic | mock
GEMINI_API_KEY=your-key-here
```

Или через UI: **Настройки → LLM Provider**.

---

---

# Проект 2 — Parser Microservice

> **Микросервис парсинга геосервисов:** сбор данных с Яндекс.Карт и 2ГИС, мониторинг репутации компании, поиск упоминаний в сети и анализ негативных отзывов.

## Обзор Parser

Parser Microservice — лёгкий автономный сервис для работы с геосервисами и агрегаторами отзывов. Не требует PostgreSQL или Celery — хранит данные в SQLite и синхронизирует их в Google Sheets.

| Модуль | Назначение |
|--------|-----------|
| 🗺️ **Карточки Яндекс.Карт** | Сбор рейтинга, количества отзывов, контактов организации |
| 🏙️ **Карточки 2ГИС** | То же, но для 2ГИС (с обходом капч и анти-бот защиты) |
| 👁️ **Мониторинг отзывов** | Сбор свежих отзывов с карточки организации (Яндекс.Карты / 2ГИС) |
| 🏆 **Анализ конкурентов** | Поиск ближайших конкурентов по геокоординатам, их рейтинги и реклама |
| ⭐ **Мониторинг репутации** | Автоматический поиск компании во всех агрегаторах (2ГИС, Зун, Prodoctorov и др.) |
| 📢 **Поиск упоминаний** | Поиск страниц, где упоминается сайт компании |
| 🔴 **Поиск негатива** | Поиск страниц с негативными отзывами по кластеру запросов |

---

## Архитектура Parser

```
┌──────────────────────────────────┐
│     FastAPI :8000                │
│     (REST + Streaming NDJSON)    │
│                                  │
│   ┌──────────────────────┐       │
│   │  Static Frontend      │       │
│   │  (index.html + JS)    │       │
│   └──────────────────────┘       │
│                                  │
│   ┌──────────────────────┐       │
│   │   Playwright         │       │
│   │  (Chromium headless) │       │
│   │  + playwright-stealth│       │
│   └──────────────────────┘       │
│                                  │
│   ┌──────────┐ ┌───────────────┐ │
│   │  SQLite  │ │ Google Sheets │ │
│   │  (JSON)  │ │  (gspread)    │ │
│   └──────────┘ └───────────────┘ │
└──────────────────────────────────┘
```

Сервис полностью автономен и разворачивается одним Docker-контейнером.

---

## Модули парсера

### 1. Парсинг карточки организации (Яндекс.Карты)

**Сервис:** `app/services/yandex_maps.py`

- Открывает URL карточки через Playwright (stealth-режим).
- Извлекает: название, адрес, телефон, сайт, рейтинг, количество отзывов, категорию.
- Обходит стандартные антибот-проверки Яндекса.

---

### 2. Парсинг карточки организации (2ГИС)

**Сервис:** `app/services/twogis_parser.py`

- Та же логика, адаптированная под DOM 2ГИС.
- Обработка страницы предупреждения об устаревшем браузере (`#acceptRiskButton`).
- Обход капчи 2ГИС через случайные задержки и stealth.
- Поддерживает 3 операции: карточка, мониторинг отзывов, анализ конкурентов.

---

### 3. Мониторинг отзывов

**Сервисы:** `app/services/reviews_monitor.py` (Яндекс), `twogis_parser.py` (2ГИС)

- Прокручивает список отзывов.
- Извлекает: автор, дата, рейтинг, текст, ответ организации.
- Сортирует по дате, фильтрует по диапазону.

---

### 4. Анализ конкурентов на геосервисах

**Сервисы:** `app/services/competitors_analysis.py` (Яндекс), `twogis_parser.py` (2ГИС)

- Формирует поисковой запрос с геокоординатами и радиусом поиска.
- Парсит список компаний из поисковой выдачи карт.
- Для каждого конкурента: название, URL, рейтинг, количество отзывов, наличие рекламы.
- Собирает топ негативных отзывов (оценка ≤ 3) для каждого конкурента.
- Результаты сохраняются в SQLite и синхронизируются в Google Sheets.

---

### 5. Мониторинг репутации

**Сервис:** `app/services/reputation_search.py`

Полный pipeline:

1. Формирует поисковой запрос: `{направление} {компания} {город} отзывы`.
2. Ищет агрегаторы через **DuckDuckGo** (без браузера, без капчи).
3. Парсит найденные агрегаторы батчами по 5 через Playwright + stealth:
   - Извлекает рейтинг и количество отзывов из JSON-LD, микроразметки, CSS-селекторов.
   - Поддерживает специфичные парсеры для 2ГИС, Зун, Prodoctorov, Napopravku и др.
4. Оценивает **релевантность** каждой страницы (скоринг: название компании, город, адрес, сайт).
5. Сравнивает с предыдущим результатом — вычисляет `rating_change`, `reviews_count_change`.
6. Делает **скриншот** страницы (если данные изменились).
7. Сохраняет в SQLite и Google Sheets (отдельный лист на компанию с круговой диаграммой).

**Ответ стримится** через NDJSON (`application/x-ndjson`) с прогресс-апдейтами в реальном времени.

---

### 6. Поиск упоминаний

**Сервис:** `app/services/mentions_search.py`

- Строит запрос: `{компания} {город} "{домен_сайта}"`.
- Ищет через DuckDuckGo (до 30 результатов).
- Для каждого найденного сайта через Playwright проверяет наличие домена компании в `href` или тексте.
- Возвращает список с флагом `is_link_present`.
- Сохраняет историю в SQLite.

---

### 7. Поиск негатива

**Сервис:** `app/services/negative_search.py`

- Принимает **кластер поисковых запросов** (несколько фраз).
- Для каждого запроса ищет результаты через DuckDuckGo.
- Парсит найденные страницы через Playwright:
  - Извлекает все оценки с `itemprop="ratingValue"` и CSS-паттернов.
  - Считает количество негативных оценок (≤ 3.9 из 5 или ≤ 8.9 из 10).
- Стримит прогресс через NDJSON.
- Сохраняет результаты в SQLite.

---

### 8. Управление проектами

**Сервис:** `app/services/projects_db.py`

- CRUD для проектов (SQLite, JSON-сериализация).
- Каждый проект: название, URL, контактные данные, координаты, URL на картах.
- **Сканирование проекта** (`project_scanner.py`) — проверяет доступность всех URL проекта.

---

### 9. Google Sheets

**Сервис:** `app/services/google_sheets.py`

| Функция | Лист | Данные |
|---------|------|--------|
| `append_reputation_results_to_sheet` | Название компании | Рейтинг, отзывы, изменения, скриншот, диаграмма |
| `append_competitors_results_to_sheet` | Запрос | Конкуренты: рейтинг, реклама, негативные отзывы |

Автоматически создаёт новые листы и добавляет **круговую диаграмму** распределения рейтингов при создании листа репутации.

---

## Стек Parser

| Компонент | Технология |
|-----------|-----------|
| Web-фреймворк | FastAPI + Uvicorn |
| Браузерная автоматизация | Playwright (Chromium headless) + playwright-stealth |
| Парсинг HTML | BeautifulSoup4 |
| Поиск в интернете | DuckDuckGo Search (ddgs) |
| HTTP-клиент | httpx |
| База данных | SQLite (JSON-файлы в `app/data/`) |
| Google Sheets | gspread + google-auth |
| Валидация данных | Pydantic v2 |
| Логирование | loguru |
| Парсинг дат | dateparser |
| Контейнеризация | Docker |

---

## Быстрый старт Parser

### Требования

- Docker (рекомендуется) или Python 3.11+
- Файл `credentials.json` с сервисным аккаунтом Google (для Google Sheets)

### Вариант 1: Docker (рекомендуется)

```bash
cd parser_microservice

# Поместите credentials.json в корень parser_microservice/
docker compose up --build
```

| Адрес | Описание |
|-------|---------|
| http://localhost:8000/ | Встроенный фронтенд |
| http://localhost:8000/docs | Swagger UI |

### Вариант 2: Локально без Docker

```bash
cd parser_microservice

python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Установить браузер Playwright
playwright install chromium --with-deps

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Конфигурация Parser

### Google Sheets (обязательно для экспорта)

1. Создайте сервисный аккаунт в [Google Cloud Console](https://console.cloud.google.com/).
2. Выдайте ему права редактора на нужные Google Таблицы.
3. Скачайте JSON-ключ и сохраните как `credentials.json` в корне `parser_microservice/`.

### ID таблиц (задаются в `google_sheets.py`)

| Константа | По умолчанию | Назначение |
|-----------|------------|-----------|
| `DEFAULT_SPREADSHEET_ID` | `1udoJEPFf...` | Таблица для репутации |
| `spreadsheet_id` в `append_competitors_results_to_sheet` | `1eng4RIv...` | Таблица для конкурентов |

### Персистентность данных (Docker volumes)

```yaml
volumes:
  - ./app/data:/app/app/data                      # SQLite-файлы
  - ./app/static/screenshots:/app/app/static/screenshots  # Скриншоты
```

### Важно: память для Playwright

```yaml
shm_size: '2g'   # Обязательно! Без этого Playwright падает с OOM
```

---

## Структура Parser

```
parser_microservice/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── credentials.json          # Сервисный аккаунт Google (не коммитить!)
│
│   # HTML-дампы для отладки парсеров
├── 2gis_dump.html
├── yandex_dump.html
├── zoon_dump.html
├── prodoctorov_dump.html
├── napopravku_dump.html
├── doctu_dump.html
├── 32top_dump.html
│
└── app/
    ├── main.py               # FastAPI: все роуты
    ├── restore_from_gsheets.py  # Утилита восстановления данных
    │
    ├── schemas/
    │   └── scraper.py        # Pydantic-схемы запросов/ответов
    │
    ├── services/
    │   ├── database.py              # Инициализация SQLite
    │   ├── projects_db.py           # CRUD проектов
    │   ├── project_scanner.py       # Сканирование URL проекта
    │   │
    │   ├── yandex_maps.py           # Парсинг Яндекс.Карт (карточка)
    │   ├── reviews_monitor.py       # Парсинг отзывов Яндекс.Карт
    │   ├── competitors_analysis.py  # Конкуренты на Яндекс.Картах
    │   │
    │   ├── twogis_parser.py         # Парсинг 2ГИС (карточка + отзывы + конкуренты)
    │   │
    │   ├── reputation_search.py     # Мониторинг репутации
    │   ├── reputation_history_db.py # История репутации (SQLite)
    │   │
    │   ├── mentions_search.py       # Поиск упоминаний сайта
    │   ├── mentions_history_db.py   # История упоминаний (SQLite)
    │   │
    │   ├── negative_search.py       # Поиск негативных отзывов
    │   ├── negative_history_db.py   # История негатива (SQLite)
    │   │
    │   ├── competitors_history_db.py # История анализа конкурентов
    │   │
    │   ├── google_sheets.py         # Экспорт в Google Sheets
    │   └── site_extractors.py       # Специфичные парсеры агрегаторов
    │
    ├── data/                    # SQLite-файлы (персистентный volume)
    │   ├── projects.db
    │   ├── reputation_history.db
    │   ├── mentions_history.db
    │   ├── negative_history.db
    │   └── competitors_history.db
    │
    └── static/
        ├── index.html           # Встроенный фронтенд
        └── screenshots/         # Скриншоты агрегаторов (volume)
```

---

## API Parser

Swagger UI: **http://localhost:8000/docs**

### Парсинг геосервисов

| Метод | Путь | Описание |
|-------|------|---------|
| `POST` | `/api/v1/parse/yandex-map` | Парсинг карточки Яндекс.Карт |
| `POST` | `/api/v1/parse/reviews-monitor` | Мониторинг отзывов Яндекс.Карт |
| `POST` | `/api/v1/parse/competitors` | Анализ конкурентов Яндекс.Карт |
| `POST` | `/api/v1/parse/twogis-map` | Парсинг карточки 2ГИС |
| `POST` | `/api/v1/parse/twogis-reviews-monitor` | Мониторинг отзывов 2ГИС |
| `POST` | `/api/v1/parse/twogis-competitors` | Анализ конкурентов 2ГИС |

### Репутация

| Метод | Путь | Описание |
|-------|------|---------|
| `POST` | `/api/v1/reputation/search` | Запуск поиска репутации (streaming NDJSON) |
| `GET` | `/api/v1/reputation/history` | История поисков (фильтр `?company=`) |
| `DELETE` | `/api/v1/reputation/history/{id}` | Удалить запись |
| `PUT` | `/api/v1/reputation/history/{id}` | Обновить запись + синхронизировать в Sheets |

### Упоминания

| Метод | Путь | Описание |
|-------|------|---------|
| `POST` | `/api/v1/mentions/search` | Поиск упоминаний сайта (streaming NDJSON) |
| `GET` | `/api/v1/mentions/history` | История поисков |
| `DELETE` | `/api/v1/mentions/history/{id}` | Удалить запись |

### Негатив

| Метод | Путь | Описание |
|-------|------|---------|
| `POST` | `/api/v1/negative/search` | Поиск негативных отзывов (streaming NDJSON) |
| `GET` | `/api/v1/negative/history` | История поисков |
| `DELETE` | `/api/v1/negative/history/{id}` | Удалить запись |
| `PUT` | `/api/v1/negative/history/{id}` | Обновить результат |

### Конкуренты (история)

| Метод | Путь | Описание |
|-------|------|---------|
| `GET` | `/api/v1/competitors/history` | История анализа конкурентов |
| `DELETE` | `/api/v1/competitors/history/{id}` | Удалить запись |

### Проекты

| Метод | Путь | Описание |
|-------|------|---------|
| `GET` | `/api/v1/projects` | Список всех проектов |
| `POST` | `/api/v1/projects` | Создать проект |
| `PUT` | `/api/v1/projects/{id}` | Обновить проект |
| `DELETE` | `/api/v1/projects/{id}` | Удалить проект |
| `POST` | `/api/v1/projects/{id}/scan` | Сканировать URL проекта |

### Формат Streaming-ответов (NDJSON)

Эндпоинты поиска возвращают **потоковый ответ** `application/x-ndjson`.  
Каждая строка — отдельный JSON-объект:

```json
{"type": "progress", "message": "Обработка сайтов (пачка 1 из 6)..."}
{"type": "result",   "data": { ... полный результат ... }}
```

---

## Интеграции Parser

### Playwright + playwright-stealth

Используется для сайтов с JavaScript-рендерингом и антибот-защитой:
- **Cloudflare** / **ServicePipe** (napopravku.ru, prodoctorov.ru)
- Капча 2ГИС
- Антибот Яндекс.Карт

Stealth имитирует реальный браузер: убирает признаки автоматизации из `navigator`, `window.chrome` и пр.

### DuckDuckGo Search (ddgs)

Используется для поиска агрегаторов, упоминаний и страниц с негативом.  
Не требует API-ключей и не блокирует при разумных нагрузках.

### site_extractors.py — специфичные парсеры

| Домен | Что извлекается |
|-------|----------------|
| `2gis.ru` | Рейтинг и количество оценок |
| `zoon.ru` | Рейтинг из `.rating-value` |
| `prodoctorov.ru` | AggregateRating из JSON-LD |
| `napopravku.ru` | AggregateRating из JSON-LD |
| другие | JSON-LD → Microdata → CSS-эвристика → Regex |

---

## Разработка Parser

### Добавление нового агрегатора

1. Добавьте домен в `site_extractors.py` → `try_extract_specific()`.
2. Реализуйте парсер для конкретной структуры HTML.
3. Протестируйте на дампе страницы (HTML-файлы в корне проекта).

### HTML-дампы для тестирования

| Файл | Источник |
|------|---------|
| `2gis_dump.html` | 2ГИС |
| `yandex_dump.html` | Яндекс.Карты |
| `zoon_dump.html` | Zoon.ru |
| `prodoctorov_dump.html` | Prodoctorov.ru |
| `napopravku_dump.html` | Napopravku.ru |
| `doctu_dump.html` | Doctu.ru |
| `32top_dump.html` | 32top.ru |

### Scratch-скрипты

```
parser_microservice/scratch/
└── test_neg.py   # Ручное тестирование поиска негатива
```

### Восстановление данных из Google Sheets

```bash
python app/restore_from_gsheets.py
```

Позволяет восстановить локальную SQLite-базу из Google Таблиц (например, после потери `app/data/`).

---

---

# Связь между проектами

Оба проекта **независимы** и могут использоваться по отдельности.

| Сценарий | AutoSEO | Parser Microservice |
|----------|---------|---------------------|
| SEO-анализ конкурентов (домены, трафик, ссылки) | ✅ Модуль "Анализ конкурентов" | — |
| Конкуренты на картах (геосервисы, рейтинги) | — | ✅ `/parse/competitors`, `/parse/twogis-competitors` |
| Репутация компании на агрегаторах | — | ✅ `/reputation/search` |
| Линкбилдинг (бесплатные и платные ссылки) | ✅ Модули 2 и 3 | — |
| Мониторинг упоминаний сайта | — | ✅ `/mentions/search` |
| Генерация alt-тегов | ✅ Модуль 4 | — |
| Экспорт в Google Sheets | ✅ (alt-теги) | ✅ (репутация, конкуренты) |

---

## Лицензия

Внутренние инструменты. Все права защищены.
