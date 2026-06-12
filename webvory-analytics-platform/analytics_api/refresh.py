"""
Refresh Script for Webvory Analytics.

Refreshes:
    - Materialized views (revenue_trends, top_customers)
    - analytics_summary table (inserts a fresh row)

Run manually:
    python -m analytics_api.refresh

Or run continuously (every 5 min) using --loop:
    python -m analytics_api.refresh --loop
"""

import sys
import time
from sqlalchemy import text
from database.connection import engine

REFRESH_INTERVAL_SECONDS = 300  # 5 minutes


SUMMARY_INSERT_SQL = """
INSERT INTO analytics_summary (
    total_orders, total_revenue, total_refunds, total_refund_amount,
    net_revenue, avg_order_value, repeat_customer_revenue
)
SELECT
    (SELECT COUNT(*) FROM orders WHERE status = 'completed'),
    (SELECT COALESCE(SUM(amount), 0) FROM orders WHERE status = 'completed'),
    (SELECT COUNT(*) FROM refunds),
    (SELECT COALESCE(SUM(refund_amount), 0) FROM refunds),
    (SELECT COALESCE(SUM(amount), 0) FROM orders WHERE status = 'completed')
        - (SELECT COALESCE(SUM(refund_amount), 0) FROM refunds),
    (SELECT COALESCE(AVG(amount), 0) FROM orders WHERE status = 'completed'),
    (
        SELECT COALESCE(SUM(o.amount), 0)
        FROM orders o
        WHERE o.status = 'completed'
        AND o.customer_id IN (
            SELECT customer_id FROM orders
            WHERE status = 'completed'
            GROUP BY customer_id
            HAVING COUNT(*) > 1
        )
    );
"""


def refresh_all():
    start = time.time()
    with engine.connect() as conn:
        print("Refreshing materialized view: revenue_trends...")
        conn.execute(text("REFRESH MATERIALIZED VIEW revenue_trends;"))

        print("Refreshing materialized view: top_customers...")
        conn.execute(text("REFRESH MATERIALIZED VIEW top_customers;"))

        print("Updating analytics_summary...")
        conn.execute(text(SUMMARY_INSERT_SQL))

        # Keep table small - retain only latest 100 summary rows
        conn.execute(text("""
            DELETE FROM analytics_summary
            WHERE id NOT IN (
                SELECT id FROM analytics_summary ORDER BY id DESC LIMIT 100
            );
        """))

        conn.commit()

    elapsed = time.time() - start
    print(f"Refresh complete in {elapsed:.2f}s\n")


if __name__ == "__main__":
    if "--loop" in sys.argv:
        print(f"Running refresh every {REFRESH_INTERVAL_SECONDS}s. Ctrl+C to stop.\n")
        while True:
            refresh_all()
            time.sleep(REFRESH_INTERVAL_SECONDS)
    else:
        refresh_all()