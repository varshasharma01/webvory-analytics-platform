"""
Mock API for Webvory Backend Assignment
Serves customers, orders, refunds data from CSVs with pagination.
Simulates a real third-party data provider.

Run:
    uvicorn mock_api.main:app --reload --port 8001
"""

import csv
import math
from pathlib import Path
from fastapi import FastAPI, Query, HTTPException

app = FastAPI(
    title="Webvory Mock API",
    description="Simulated third-party data provider — customers, orders, refunds",
    version="1.0.0",
)

DATA_DIR = Path(__file__).resolve().parent.parent / "generated_data"


# ──────────────────────────────────────────────
# Load CSVs into memory at startup
# ──────────────────────────────────────────────

def load_csv(filename: str):
    path = DATA_DIR / filename
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


print("Loading mock data into memory... (this may take ~30-60s for orders)")
CUSTOMERS = load_csv("customers.csv")
ORDERS    = load_csv("orders.csv")
REFUNDS   = load_csv("refunds.csv")
print(f"Loaded: {len(CUSTOMERS):,} customers | {len(ORDERS):,} orders | {len(REFUNDS):,} refunds")


# ──────────────────────────────────────────────
# Generic Pagination Helper
# ──────────────────────────────────────────────

def paginate(data: list, page: int, size: int):
    total = len(data)
    total_pages = math.ceil(total / size) if total else 0

    if page < 1:
        raise HTTPException(status_code=422, detail="page must be >= 1")
    if size < 1 or size > 5000:
        raise HTTPException(status_code=422, detail="size must be between 1 and 5000")

    start = (page - 1) * size
    end = start + size

    return {
        "page": page,
        "size": size,
        "total": total,
        "total_pages": total_pages,
        "data": data[start:end],
    }


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "message": "Webvory Mock API",
        "endpoints": ["/customers", "/orders", "/refunds"],
        "docs": "/docs",
    }


@app.get("/customers")
def get_customers(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(1000, ge=1, le=5000, description="Records per page"),
):
    return paginate(CUSTOMERS, page, size)


@app.get("/orders")
def get_orders(
    page: int = Query(1, ge=1),
    size: int = Query(1000, ge=1, le=5000),
):
    return paginate(ORDERS, page, size)


@app.get("/refunds")
def get_refunds(
    page: int = Query(1, ge=1),
    size: int = Query(1000, ge=1, le=5000),
):
    return paginate(REFUNDS, page, size)