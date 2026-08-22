# 🏞️ Coochbehar Travels Backend API

> **Tour Marketing + Visitor Analytics + Enquiry & Lead-Generation System**

A modern, scalable backend architecture built with **FastAPI**, **SQLAlchemy 2.0**, **Alembic**, and **UV**. This system empowers tour operators and travel agencies to manage tour packages, capture and analyze web visitor traffic, process custom enquiries, and score sales leads seamlessly.

---

## 🌟 Key Features

### 1. 🎯 Tour Marketing Engine
* **Tour Packages & Pricing**: Manage multi-day tour itineraries, highlights, route stops, and media galleries.
* **Departures & Scheduling**: Real-time management of active tour departures, seat limits, and availability.
* **Accommodations & Transport**: Integrated hotel room management and vehicle fleet listings.
* **Reviews & Ratings**: Verified customer reviews and rating calculations for packages.

### 2. 📊 Visitor Analytics Tracking
* **Visitor Identity**: Track anonymous visitors across web sessions using unique UUID identifiers.
* **Session Telemetry**: Track session durations, entry/exit pages, referrer sources, device types, and locations.
* **Granular Event Logs**: Record user interaction events (clicks, package views, enquiry button triggers, form drop-offs).

### 3. 💼 Enquiry & Lead-Generation System
* **Automated Lead Scoring**: Calculate lead scores dynamically based on visitor behavior and engagement depth.
* **Custom Tour Enquiries**: Process tailored travel requests including budgets, group sizes, and custom requirements.
* **Direct Bookings**: Manage hotel room bookings and vehicle rental reservations.
* **Sales Pipeline Management**: Lead status tracking (`new`, `contacted`, `qualified`, `converted`, `lost`) and sales team assignment.

---

## 🛠️ Technology Stack

| Component | Tech |
| :--- | :--- |
| **Language** | Python 3.14+ |
| **Framework** | [FastAPI](https://fastapi.tiangolo.com/) |
| **Package Manager** | [UV](https://github.com/astral-sh/uv) |
| **ORM** | [SQLAlchemy 2.0](https://www.sqlalchemy.org/) |
| **Migrations** | [Alembic](https://alembic.sqlalchemy.org/) |
| **Database** | PostgreSQL (`psycopg3`) / MySQL (`pymysql`) |
| **API Reference** | [Scalar API Reference](https://github.com/scalar/scalar) (`scalar-fastapi`) |

---

## 📂 Exact Project Structure

```text
Coochbehar-Travels/
├── .env                                  # Environment variables configuration
├── .gitignore                            # Git ignore paths
├── .python-version                       # Python runtime specification
├── README.md                             # Project documentation
├── alembic.ini                           # Alembic configuration
├── pyproject.toml                        # Project dependencies & build settings
├── schema.sql                            # Database schema SQL dump
├── uv.lock                               # Locked dependency resolution tree
│
├── alembic/                              # Alembic Database Migrations
│   ├── README
│   ├── env.py                            # Migration environment script
│   ├── script.py.mako                    # Migration file generation template
│   └── versions/                         # Migration scripts folder
│       ├── 0dbda10269c2_create_travel_models.py
│       ├── 1ea1e27a822b_update_travel_database.py
│       ├── 331314bca490_update_travel_database.py
│       ├── 460cc29ba7ef_update_travel_database.py
│       ├── 4a63850aeba4_update_travel_database.py
│       ├── 6afe40f9288f_update_travel_database.py
│       ├── a0d5c38c7192_create_travel_models.py
│       ├── b12268fad676_initial_migration.py
│       └── fd467279d917_update_travel_database.py
│
└── app/                                  # Main Application Source
    ├── __init__.py
    ├── main.py                           # FastAPI application entry point & routes
    │
    ├── api/                              # API Layer
    │   ├── serializer/                   # Data serialization schemas
    │   ├── v1/                           # API Version 1
    │   │   └── endpoints/                # Route handlers / controllers
    │   └── v2                            # Future API Version 2 stub
    │
    ├── core/                             # Core Application Configuration
    │   └── config.py                     # Environment settings loader
    │
    ├── db/                               # Database Configuration
    │   └── database.py                   # Engine initialization & session dependency
    │
    ├── middleware/                       # Custom HTTP Middlewares
    │
    ├── models/                           # SQLAlchemy Data Models
    │   ├── __init__.py                   # Central export for all ORM models
    │   ├── base.py                       # Declarative Base class
    │   ├── lead.py                       # Lead management model
    │   ├── review.py                     # Package reviews model
    │   ├── room.py                       # Hotel room inventory model
    │   ├── tour_departure.py             # Scheduled tour departure model
    │   ├── tour_gallery.py               # Tour photo/video media model
    │   ├── tour_highlight.py             # Tour package features model
    │   ├── tour_itinerary.py             # Daily itinerary schedule model
    │   ├── tour_package.py               # Tour package catalog model
    │   ├── tour_route_stop.py            # Key transit stops & locations model
    │   ├── user.py                       # System user & admin model
    │   ├── vehicle.py                    # Transport vehicle fleet model
    │   ├── visitor.py                    # Web visitor identifier model
    │   ├── visitor_event.py              # Granular visitor event tracking model
    │   └── visitor_session.py            # Visitor navigation session model
    │
    ├── repository/                       # Data Access Layer (Repositories)
    ├── schemas/                          # Pydantic Schemas (Request/Response)
    ├── services/                         # Business Logic Layer
    └── utils/                            # Shared Utilities & Helpers
```

---

## 🚀 Setup & System Startup Guide

### 1. Prerequisites
Ensure you have **Python 3.14+** and **[uv](https://astral.sh/uv)** installed.

### 2. Environment Configuration
Create a `.env` file in the root directory (or update existing `.env`):

```env
DATABASE_URL=postgresql+psycopg://USERNAME:PASSWORD@HOST:PORT/DATABASE
CORS_ORIGINS=https://your-frontend.onrender.com
UPLOAD_MAX_SIZE_BYTES=10485760
UPLOAD_ALLOWED_FOLDERS=tour-packages,customers,users,vehicles,rooms,reviews
```

Set `CORS_ORIGINS` in Render to the exact browser origin(s) that call this API,
separated by commas. Include the scheme and port when needed, but do not add a
trailing slash. For example:

```env
CORS_ORIGINS=https://coochbehartravels.com,https://admin.coochbehartravels.com
```

The file endpoint is `POST /api/v1/public/files/upload`. It requires the standard
Bearer JWT and is available to authenticated admin, staff, and customer actors.

The endpoint validates the JWT, file size, media type, and allowed folder before
uploading to Cloudinary. Save the returned `public_id` in the relevant business
record when associating the uploaded file.

*Example for local PostgreSQL:*
```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/coochbehar_travels
```

---

### 3. Database Setup & Alembic Migrations

Execute database migrations using `uv` to ensure your database schema is up to date:

1. **Generate New Migration Revision** (when SQLAlchemy models are updated):
   ```bash
   uv run python -m alembic revision --autogenerate -m "create travel models"
   ```

2. **Apply Migrations to Database**:
   ```bash
   uv run python -m alembic upgrade head
   ```

#### Additional Helper Commands:
* **Check Migration Status**:
  ```bash
  uv run python -m alembic current
  ```
* **Verify Schema & Model Sync**:
  ```bash
  uv run python -m alembic check
  ```
* **Rollback Last Migration**:
  ```bash
  uv run python -m alembic downgrade -1
  ```
* **Admin Seed Script**
  ```bash
  uv run python scripts/seed_admin.py
  ```
---

### 4. Running the Development Server

Start the FastAPI application server with hot-reloading enabled:

```bash
uv run uvicorn app.main:app --reload
```
*(Or via python module launcher if using Windows UV wrapper)*:
```bash
uv run python -m uvicorn app.main:app --reload
```

The application will start running at: `http://127.0.0.1:8000`

---

## 📑 Interactive Documentation with Scalar

This project exclusively uses **Scalar API Reference** (via `scalar-fastapi`) as its primary documentation UI framework (replacing standard Swagger UI).

Once the server is running, access the interactive Scalar API documentation at:

* 🌈 **Scalar Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) (or [http://127.0.0.1:8000/scalar](http://127.0.0.1:8000/scalar))

### Enquiry API

End-user enquiry routes are grouped under `/api/v1/enquiries`:

| Method | Path | Purpose |
| :--- | :--- | :--- |
| `POST` | `/api/v1/enquiries` | Submit an enquiry and create its sales lead. |
| `POST` | `/api/v1/enquiries/custom` | Submit a custom tour request and create its sales lead. |
| `GET` | `/api/v1/admin/enquiries` | List enquiries with optional status and type filters. |
| `GET` | `/api/v1/admin/enquiries/{enquiry_id}` | Retrieve an enquiry, including custom tour and requester contact fields. |
| `PATCH` | `/api/v1/admin/enquiries/{enquiry_id}` | Update enquiry status, subject, or message. |

Custom requests are stored in `enquiries` with `enquiry_type=CUSTOM_TOUR`. Their `name` and `mobile` values are persisted as `enquirer_name` and `enquirer_phone`, and the linked `leads` row is created automatically.

---

## 🗄️ Database Architecture & Entities

```mermaid
erDiagram
    VISITOR ||--o{ VISITOR_SESSION : "initiates"
    VISITOR_SESSION ||--o{ VISITOR_EVENT : "logs"
    VISITOR ||--o{ ENQUIRY : "submits"
    CUSTOMER ||--o{ ENQUIRY : "submits"
    ENQUIRY ||--o| LEAD : "creates"
    LEAD ||--o{ LEAD_ACTIVITY : "records"
    
    TOUR_PACKAGE ||--o{ TOUR_ITINERARY : "contains"
    TOUR_PACKAGE ||--o{ TOUR_HIGHLIGHT : "features"
    TOUR_PACKAGE ||--o{ TOUR_GALLERY : "includes"
    TOUR_PACKAGE ||--o{ TOUR_DEPARTURE : "schedules"
    TOUR_PACKAGE ||--o{ REVIEW : "receives"
    
    ROOM ||--o{ ROOM_BOOKING : "booked in"
    VEHICLE ||--o{ VEHICLE_BOOKING : "reserved in"
```

