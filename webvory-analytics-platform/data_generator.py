"""
Data Generator for Webvory Backend Assignment
Generates: 100,000 Customers | 1,000,000 Orders | 200,000 Refunds
Reproducible via fixed SEED = 42
"""

import random
import csv
import os
from datetime import datetime, timedelta
from faker import Faker

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
SEED             = 42
NUM_CUSTOMERS    = 100_000
NUM_ORDERS       = 1_000_000
NUM_REFUNDS      = 200_000
OUTPUT_DIR       = "generated_data"

random.seed(SEED)
fake = Faker()
Faker.seed(SEED)

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def random_date(start_year=2022, end_year=2024):
    start = datetime(start_year, 1, 1)
    end   = datetime(end_year, 12, 31)
    delta = end - start
    return start + timedelta(days=random.randint(0, delta.days))


# ──────────────────────────────────────────────
# 1. CUSTOMERS
# ──────────────────────────────────────────────

def generate_customers():
    print(f"Generating {NUM_CUSTOMERS:,} customers...")
    path = os.path.join(OUTPUT_DIR, "customers.csv")

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["customer_id", "name", "email", "phone", "city", "country", "created_at"])

        for i in range(1, NUM_CUSTOMERS + 1):
            writer.writerow([
                i,
                fake.name(),
                fake.unique.email(),
                fake.phone_number()[:15],
                fake.city(),
                fake.country_code(),
                random_date(2020, 2022).date(),
            ])

            if i % 10_000 == 0:
                print(f"  Customers: {i:,} done")

    print(f"  Saved → {path}\n")


# ──────────────────────────────────────────────
# 2. ORDERS
# ──────────────────────────────────────────────

ORDER_STATUSES = ["completed", "pending", "cancelled", "shipped"]
# Weight: mostly completed so revenue numbers make sense
STATUS_WEIGHTS = [0.65, 0.15, 0.10, 0.10]

def generate_orders():
    print(f"Generating {NUM_ORDERS:,} orders...")
    path = os.path.join(OUTPUT_DIR, "orders.csv")

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "order_id", "customer_id", "order_date",
            "amount", "status", "product_category"
        ])

        categories = ["Electronics", "Clothing", "Books", "Home", "Sports", "Food", "Beauty"]

        for i in range(1, NUM_ORDERS + 1):
            writer.writerow([
                i,
                random.randint(1, NUM_CUSTOMERS),          # FK → customers
                random_date(2022, 2024).date(),
                round(random.uniform(5.0, 5000.0), 2),     # order amount
                random.choices(ORDER_STATUSES, STATUS_WEIGHTS)[0],
                random.choice(categories),
            ])

            if i % 100_000 == 0:
                print(f"  Orders: {i:,} done")

    print(f"  Saved → {path}\n")


# ──────────────────────────────────────────────
# 3. REFUNDS
# ──────────────────────────────────────────────

def generate_refunds():
    print(f"Generating {NUM_REFUNDS:,} refunds...")
    path = os.path.join(OUTPUT_DIR, "refunds.csv")

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "refund_id", "order_id", "customer_id",
            "refund_date", "refund_amount", "reason"
        ])

        reasons = ["Damaged", "Wrong item", "Not as described", "Changed mind", "Delayed delivery"]

        # Refunds reference a subset of orders (first 500k for simplicity)
        used_orders = random.sample(range(1, 500_001), NUM_REFUNDS)

        for i, order_id in enumerate(used_orders, start=1):
            writer.writerow([
                i,
                order_id,
                random.randint(1, NUM_CUSTOMERS),
                random_date(2022, 2024).date(),
                round(random.uniform(5.0, 500.0), 2),
                random.choice(reasons),
            ])

            if i % 20_000 == 0:
                print(f"  Refunds: {i:,} done")

    print(f"  Saved → {path}\n")


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────

if __name__ == "__main__":
    start = datetime.now()
    print("=" * 50)
    print("  Webvory Data Generator  |  SEED =", SEED)
    print("=" * 50 + "\n")

    generate_customers()
    generate_orders()
    generate_refunds()

    elapsed = (datetime.now() - start).seconds
    print("=" * 50)
    print(f"  All done in {elapsed}s")
    print(f"  Files in: ./{OUTPUT_DIR}/")
    print("=" * 50)