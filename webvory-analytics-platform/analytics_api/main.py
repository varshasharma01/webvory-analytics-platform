"""
Analytics API for Webvory Backend Assignment.

Exposes:
    GET /analytics/summary           -> total orders, revenue, refunds,
                                         net revenue, avg order value,
                                         repeat customer revenue
    GET /analytics/revenue-trends    -> monthly revenue trend
    GET /analytics/top-customers     -> top N customers by spend

All endpoints read from pre-aggregated tables/materialized views
and are wrapped with Redis caching (TTL = 120s).

Run:
    uvicorn analytics_api.main:app --reload --port 8000
"""

from fastapi import FastAPI, Query
from sqlalchemy import text
from database.connection import SessionLocal
from analytics_api.cache import cached_query

app = FastAPI(
    title="Webvory Analytics API",
    description="Pre-aggregated business analytics with sub-2s response times",
    version="1.0.0",
)


# ──────────────────────────────────────────────
# /analytics/summary
# ──────────────────────────────────────────────

def _fetch_summary():
    db = SessionLocal()
    try:
        row = db.execute(text("""
            SELECT total_orders, total_revenue, total_refunds,
                   total_refund_amount, net_revenue, avg_order_value,
                   repeat_customer_revenue, updated_at
            FROM analytics_summary
            ORDER BY id DESC
            LIMIT 1;
        """)).fetchone()

        if row is None:
            return {"error": "No summary data yet. Run refresh script."}

        return {
            "total_orders": row.total_orders,
            "total_revenue": float(row.total_revenue),
            "total_refunds": row.total_refunds,
            "total_refund_amount": float(row.total_refund_amount),
            "net_revenue": float(row.net_revenue),
            "avg_order_value": float(row.avg_order_value),
            "repeat_customer_revenue": float(row.repeat_customer_revenue),
            "last_updated": str(row.updated_at),
        }
    finally:
        db.close()


@app.get("/analytics/summary")
def get_summary():
    """
    Returns: total orders, total revenue, total refunds, net revenue,
    average order value, and repeat customer revenue.

    Source: analytics_summary table (pre-aggregated, refreshed every 5 min)
    Cache: Redis, 120s TTL
    """
    return cached_query("analytics:summary", _fetch_summary)


# ──────────────────────────────────────────────
# /analytics/revenue-trends
# ──────────────────────────────────────────────

def _fetch_revenue_trends():
    db = SessionLocal()
    try:
        rows = db.execute(text("""
            SELECT month, order_count, revenue
            FROM revenue_trends
            ORDER BY month;
        """)).fetchall()

        return {
            "trends": [
                {
                    "month": str(r.month),
                    "order_count": r.order_count,
                    "revenue": float(r.revenue),
                }
                for r in rows
            ]
        }
    finally:
        db.close()


@app.get("/analytics/revenue-trends")
def get_revenue_trends():
    """
    Returns monthly order count and revenue.

    Source: revenue_trends materialized view (refreshed every 5 min)
    Cache: Redis, 120s TTL
    """
    return cached_query("analytics:revenue_trends", _fetch_revenue_trends)


# ──────────────────────────────────────────────
# /analytics/top-customers
# ──────────────────────────────────────────────

def _fetch_top_customers(limit: int):
    db = SessionLocal()
    try:
        rows = db.execute(text("""
            SELECT customer_id, name, email, order_count, total_spend
            FROM top_customers
            ORDER BY total_spend DESC
            LIMIT :limit;
        """), {"limit": limit}).fetchall()

        return {
            "limit": limit,
            "customers": [
                {
                    "customer_id": r.customer_id,
                    "name": r.name,
                    "email": r.email,
                    "order_count": r.order_count,
                    "total_spend": float(r.total_spend),
                }
                for r in rows
            ],
        }
    finally:
        db.close()


@app.get("/analytics/top-customers")
def get_top_customers(limit: int = Query(10, ge=1, le=100)):
    """
    Returns top N customers ranked by total completed-order spend.

    Source: top_customers materialized view (refreshed every 5 min)
    Cache: Redis, 120s TTL (cache key includes limit)
    """
    cache_key = f"analytics:top_customers:{limit}"
    return cached_query(cache_key, lambda: _fetch_top_customers(limit))


# ──────────────────────────────────────────────
# Health check
# ──────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "message": "Webvory Analytics API",
        "endpoints": [
            "/analytics/summary",
            "/analytics/revenue-trends",
            "/analytics/top-customers",
        ],
        "docs": "/docs",
    }
