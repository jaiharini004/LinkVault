# LinkVault: Smart Link Knowledge Hub

LinkVault is a smart, automated bookmarking and knowledge hub designed to bridge informal communication streams (like WhatsApp, Telegram, or Slack) with a structured, resilient link management system. It aims to eliminate the friction of chat-based resource sharing by acting as a highly organized, searchable, and intelligent repository for all your links.

## 🚀 Features

- **Automated Metadata Scraping:** Fail-safe, non-blocking extraction of titles, descriptions, and favicons from destination URLs.
- **WhatsApp Chat Import Parser:** Easily ingest exported WhatsApp `.txt` chat histories. The system extracts links, infers context from surrounding chat messages, and auto-assigns platform categories.
- **Smart Duplicate Detection:** Uses $O(1)$ SHA-256 hash lookups on normalized URLs to instantly identify duplicates before they are stored, automatically stripping tracking tags (like `utm_*`, `fbclid`, etc.).
- **Background Health Monitoring:** An asynchronous, non-blocking ThreadPoolExecutor worker that regularly checks the HTTP reachability of your saved links, tagging them as `Healthy`, `Broken`, `Restricted`, or `Timeout/Unreachable`.
- **Quick Inbox Staging:** Dump raw URLs into an unorganized inbox staging queue. Process and batch-organize them into specific vaults with suggested categories later.
- **Dynamic Multi-Criteria Search:** A powerful REST API allowing real-time searching across text queries, categories, link health, source provenance, and inbox status using SQLAlchemy.

## 🛠️ Tech Stack

- **Backend Framework:** Python 3, Flask, Flask-SQLAlchemy (ORM), Flask-Migrate
- **Database:** SQLite (default for local development, easily swappable to PostgreSQL)
- **Concurrency & Background Jobs:** Python native `concurrent.futures.ThreadPoolExecutor`
- **Data Scraping & Requests:** `requests`, `BeautifulSoup4`
- **Testing:** Python `unittest`, `unittest.mock`

## 🏗️ Architecture

The application is built on a modular Blueprint architecture, heavily utilizing the Service Repository pattern to separate business logic from routing.

- **Routes (`app/routes/`)**: Expose the RESTful API endpoints and handle HTTP request/response formatting.
- **Services (`app/services/`)**: Contain the core business intelligence—from parsing WhatsApp text logs and hashing URLs, to scraping metadata and pinging servers for health checks.
- **Models (`app/models/`)**: Define the database schema using SQLAlchemy. The `Link` model is extended significantly to handle provenance, health states, and normalized hashes.

## 📁 Folder Structure

```text
smart-link-organizer/
├── app/
│   ├── __init__.py                # Flask app factory & extensions setup
│   ├── extensions.py              # Centralized extension initialization (db, migrate)
│   ├── models/                    # Database models
│   │   ├── link.py                # Core Link & Category models
│   │   └── short_url.py           # Shortened URL models
│   ├── routes/                    # API Endpoints
│   │   ├── health_routes.py       # Health trigger endpoints
│   │   ├── import_routes.py       # WhatsApp chat import endpoints
│   │   ├── inbox_routes.py        # Inbox staging area endpoints
│   │   └── link_routes.py         # Search and duplicate detection endpoints
│   └── services/                  # Business Logic layer
│       ├── health_service.py      # Background HTTP health worker
│       ├── inbox_service.py       # Batch organization logic
│       ├── link_service.py        # URL normalization and hashing engine
│       ├── metadata_service.py    # Fail-safe metadata scraper
│       ├── short_url_service.py   # Link shortening logic
│       ├── validation_service.py  # SSRF and search query sanitization
│       └── whatsapp_service.py    # WhatsApp chat parsing engine
├── tests/                         # Unit & Integration Tests
│   ├── test_health_service.py
│   ├── test_inbox_search.py
│   ├── test_metadata_service.py
│   ├── test_security_and_validation.py
│   └── test_whatsapp_service.py
├── config.py                      # Environment variables and configurations
├── run.py                         # Application entry point
├── requirements.txt               # Python dependencies
└── README.md                      # This file!
```

## 💻 Getting Started (Local Development)

### 1. Install Dependencies
Ensure you have Python 3.10+ installed, then install the required libraries:
```bash
pip install -r requirements.txt
```

### 2. Run the Application
Start the Flask development server. Upon running, the application will automatically create an `app.db` SQLite database in the instance folder with all the correct tables.
```bash
python run.py
```

The API will be available locally at `http://127.0.0.1:5000`.

### 3. Run the Tests
We have a comprehensive test suite covering the intelligent services. Run them using:
```bash
python -m unittest discover tests -v
```

## 🎨 UI Design System Compliance

Though this is currently a headless API, all endpoints emit JSON payloads that include pre-computed Global UI Tokens to ensure frontend developers immediately map data to the correct visual components.

- **Primary Colors:** `#1E3A8A` (Navy), `#2563EB` (Slate Blue)
- **Status Colors:** `#15803D` (Healthy), `#B91C1C` (Broken), `#B45309` (Restricted), `#64748B` (Timeout)
- **Typography:** `Segoe UI` system stack.
