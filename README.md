# DPP Management Platform — Backend

REST API for managing **Digital Product Passports (DPP)** following the [Asset Administration Shell (AAS)](https://www.plattform-i40.de/PI40/Redaktion/EN/Downloads/Publikation/Details-of-the-Asset-Administration-Shell-Part1.html) data schema. Supports JSON-based CRUD, AASX file ingestion, SPARQL queries against a semantic store, and PDF export.

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI + Uvicorn (async) |
| Database | PostgreSQL (JSONB for DPP data) |
| Semantic Store | Apache Jena Fuseki (RDF / SPARQL) |
| Auth | JWT (Bearer token) |
| Observability | Prometheus · Grafana · Loki · Promtail |
| Reverse Proxy | Nginx |
| Dependency Mgmt | Poetry |

## Requirements

- Python 3.11+
- Docker & Docker Compose
- Poetry

## Setup

### 1. Clone & configure environment

```bash
git clone <repository-url>
cd dpp-backend
cp .env.example .env
```

Edit `.env` with your values (see `.env.example` for all required variables).

### 2. Run with Docker Compose

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| API | http://localhost (via Nginx) |
| API direct | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| Fuseki | http://localhost:3030 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3001 |

> The frontend (`dpp-frontend`) must be a sibling directory — `docker compose` builds it from `../dpp-frontend`.

### 3. Run locally (without Docker)

```bash
poetry install
poetry run uvicorn app.main:app --reload
```

## API Overview

All endpoints except `/auth/login` require a `Bearer` token.

### Authentication

| Method | Path | Description |
|---|---|---|
| `POST` | `/auth/login` | Login — returns JWT access token |
| `GET` | `/auth/me` | Current authenticated user info |

### DPP — JSON

| Method | Path | Description |
|---|---|---|
| `POST` | `/dpp/json/` | Create a new DPP |
| `GET` | `/dpp/json/{id}` | Get a DPP by ID |
| `PUT` | `/dpp/json/{id}` | Update a DPP |
| `DELETE` | `/dpp/json/{id}` | Delete a DPP |
| `PUT` | `/dpp/json/{id}/publish` | Publish a DPP (makes it publicly discoverable) |
| `PUT` | `/dpp/json/{id}/unpublish` | Unpublish a DPP |
| `POST` | `/dpp/json/search` | Search DPPs (simple / advanced / SPARQL modes) |
| `GET` | `/dpp/json/stats` | Global DPP statistics |

### DPP — Files

| Method | Path | Description |
|---|---|---|
| `POST` | `/dpp/files/upload` | Upload an `.aasx` or `.zip` file — extracts and stores DPP data |
| `GET` | `/dpp/files/static/{uuid}/{path}` | Serve extracted static files (images, PDFs) |

### SPARQL / RDF

| Method | Path | Description |
|---|---|---|
| `POST` | `/dpp/sparql/query` | Execute a SPARQL SELECT query against Fuseki |
| `GET` | `/dpp/sparql/graph/{id}` | RDF graph visualization (nodes & edges JSON) |

### Export

| Method | Path | Description |
|---|---|---|
| `GET` | `/dpp/export/{id}` | Export DPP as JSON |
| `GET` | `/dpp/export/{id}/pdf` | Export DPP as PDF |

### System (Admin only)

| Method | Path | Description |
|---|---|---|
| `GET` | `/system/health` | Database & API health check |
| `GET` | `/system/logs` | Last 50 log lines |
| `GET` | `/system/config` | Running configuration (no secrets) |

## Access Control

| Role | Permissions |
|---|---|
| `admin` | Full access to all DPPs and system endpoints |
| `user` | Create/edit/delete own DPPs; view published DPPs |
| `viewer` | View published DPPs only |

User sub-roles: `manufacturer`, `technician`, `distributor`, `recycler`, `inspector`, `consumer`, `auditor`, `partner`.

## Project Structure

```
app/
├── configs/        # Settings and role definitions
├── db/             # Database engine and session
├── models/         # SQLAlchemy models
├── routers/        # API route handlers
├── schemas/        # Pydantic schemas
└── utils/          # Auth, JWT, logging, security
tests/
alembic/            # Database migrations
```

## Running Tests

```bash
poetry run pytest
```

Tests require a running PostgreSQL instance with a seeded user. Set credentials via environment variables:

```bash
API_USERNAME=your_user API_PASSWORD=your_password poetry run pytest
```
