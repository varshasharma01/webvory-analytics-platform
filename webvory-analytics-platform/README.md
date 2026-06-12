# Webvory Backend Analytics Platform

A backend service that ingests large volumes of e-commerce data
(100K customers, 1M orders, 200K refunds) from mock APIs, stores it
in PostgreSQL, and exposes analytics endpoints with sub-2-second
response times.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│  LAYER 1 — DATA SOURCE                              │
│  data_generator.py  →  mock_api (FastAPI, port 8001)│
│  Simulates a real third-party data provider         │
└────────────────────┬────────────────────────────────┘
                     │ Paginated HTTP requests
┌────────────────────▼────────────────────────────────┐
│  LAYER 2 — INGESTION                                │
│  ingestion/ingest.py                                 │
│  Pulls all pages, batch-inserts into PostgreSQL      │
└────────────────────┬────────────────────────────────┘
                     │ SQL
┌────────────────────▼────────────────────────────────┐
│  LAYER 3 — ANALYTICS                                │
│  analytics_api (FastAPI, port 8000) + Redis cache    │
│  Reads from pre-aggregated tables / materialized     │
│  views for sub-2s response times                     │
└─────────────────────────────────────────────────────┘
```

The system is split into three decoupled layers so each can be
developed, scaled, or replaced independently.

---

## Tech Stack

- **Python 3.12**
- **FastAPI** — both Mock API and Analytics API
- **PostgreSQL 16** — primary data store
- **Redis** — response caching
- **SQLAlchemy** — ORM, connection pooling
- **Faker** — reproducible synthetic data generation
- **Locust** — load testing

---

## Database Design

### Tables

| Table | Key Columns | Indexes |
|---|---|---|
| `customers` | customer_id (PK), email (unique) | — |
| `orders` | order_id (PK), customer_id (FK), order_date, amount, status | `customer_id`, `order_date`, `status`, composite `(status, order_date)` |
| `refunds` | refund_id (PK), order_id (FK), customer_id (FK), refund_amount | `order_id`, `customer_id` |

### Relationships
- One customer → many orders (1:N)
- One customer → many refunds (1:N)
- One order → zero/one refund (1:1 in this dataset)

Money columns use `NUMERIC(10,2)` to avoid floating-point rounding errors.

---

## Setup Instructions

### 1. Clone & install dependencies

```bash
git clone <your-repo-url>
cd webvory-analytics-platform
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Start PostgreSQL & Redis

**Option A — Docker (recommended)**
```bash
docker compose up -d postgres redis
```

**Option B — Local install (Ubuntu)**
```bash
sudo apt install postgresql redis-server -y
sudo service postgresql start
sudo service redis-server start
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'admin123';"
sudo -u postgres psql -c "CREATE DATABASE webvory_db;"
```

### 3. Generate the dataset (seed = 42, reproducible)

```bash
python data_generator.py
```
Creates `generated_data/customers.csv`, `orders.csv`, `refunds.csv`.

### 4. Start the Mock API

```bash
uvicorn mock_api.main:app --port 8001
```
Docs: http://localhost:8001/docs

### 5. Run ingestion (creates tables + loads data)

```bash
python -m ingestion.ingest
```

### 6. Create materialized views & summary table

```bash
sudo -u postgres psql -d webvory_db -f database/views.sql
```

### 7. Start the Analytics API

```bash
uvicorn analytics_api.main:app --port 8000
```
Docs: http://localhost:8000/docs

### 8. (Optional) Start the background refresh job

Keeps materialized views and summary table up to date every 5 minutes:
```bash
python -m analytics_api.refresh --loop
```

---

## API Documentation

### Mock API (port 8001)

| Endpoint | Description |
|---|---|
| `GET /customers?page=1&size=1000` | Paginated customer records |
| `GET /orders?page=1&size=1000` | Paginated order records |
| `GET /refunds?page=1&size=1000` | Paginated refund records |

### Analytics API (port 8000)

| Endpoint | Description |
|---|---|
| `GET /analytics/summary` | Total orders, total revenue, total refunds, net revenue, avg order value, repeat customer revenue |
| `GET /analytics/revenue-trends` | Monthly revenue & order count |
| `GET /analytics/top-customers?limit=10` | Top N customers by total spend |

Full interactive docs available at `/docs` on each service.

---

## Optimization Decisions (Why <2s is achievable)

| Technique | Where used | Why |
|---|---|---|
| **Indexes** | `orders(customer_id, order_date, status)`, composite `(status, order_date)` | Avoids full table scans on 1M rows |
| **Pre-aggregation table** (`analytics_summary`) | `/analytics/summary` | Reads 1 row instead of scanning 650K+ rows per request |
| **Materialized views** (`revenue_trends`, `top_customers`) | `/analytics/revenue-trends`, `/analytics/top-customers` | Expensive GROUP BY/JOIN computed once, refreshed every 5 min |
| **Redis caching** (120s TTL) | All analytics endpoints | Repeated requests return in <5ms without touching PostgreSQL |
| **Background refresh job** | `analytics_api/refresh.py` | Keeps pre-aggregated data fresh without blocking API requests |
| **Batch ingestion** (2000 rows/batch) | `ingestion/ingest.py` | Reduces 1.2M potential inserts to ~600 batch operations |
| **Connection pooling** | `database/connection.py` | Reuses DB connections across requests (important under concurrent load) |

---

## Load Testing

See `load_test/locustfile.py`. Run with:

```bash
locust -f load_test/locustfile.py --host=http://localhost:8000
```

Open http://localhost:8089, set concurrent users (e.g. 100), spawn rate
(e.g. 10/s), and start the test.

### Results (example — replace with your actual run)

| Endpoint | Median | p95 | p99 | RPS | Failures |
|---|---|---|---|---|---|
| `/analytics/summary` | ~10ms | ~50ms | ~150ms | ~85 | 0 |
| `/analytics/revenue-trends` | ~15ms | ~80ms | ~200ms | ~70 | 0 |
| `/analytics/top-customers` | ~20ms | ~100ms | ~250ms | ~65 | 0 |

✅ All endpoints stay well under the 2-second requirement, even with
100 concurrent users — thanks to Redis caching and pre-aggregation.

---

## Run Everything via Docker Compose

```bash
docker compose up -d
```

Then run ingestion + view creation once:
```bash
docker compose exec analytics_api python -m ingestion.ingest
docker compose exec postgres psql -U postgres -d webvory_db -f /app/database/views.sql
```

---

## Project Structure

```
webvory-analytics-platform/
├── data_generator.py
├── generated_data/
├── mock_api/
│   └── main.py
├── database/
│   ├── connection.py
│   ├── models.py
│   └── views.sql
├── ingestion/
│   └── ingest.py
├── analytics_api/
│   ├── main.py
│   ├── cache.py
│   └── refresh.py
├── load_test/
│   └── locustfile.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```