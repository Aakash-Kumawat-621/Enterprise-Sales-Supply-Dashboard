"""
load_to_db.py
=============
ETL — Phase 5a: Load processed star-schema CSVs into SQLite.

Load order (FK-safe — dimension tables before fact table):
    1. Dim_Date
    2. Dim_Product
    3. Dim_Region
    4. Dim_Customer
    5. Fact_Sales

After loading, runs SELECT COUNT(*) on every table to verify
row counts match the source CSVs.

Database: retail_analytics.db (SQLite, created in project root)
Note    : To switch to PostgreSQL, change DB_URL to a psycopg2 connection
          string. All downstream queries are standard SQL — no changes needed.
"""

import sys
import sqlite3
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# ── Configuration ─────────────────────────────────────────────────────────────
PROCESSED  = Path("data/processed")
DDL_FILE   = Path("sql/ddl_create_star_schema.sql")
DB_PATH    = Path("retail_analytics.db")
DB_URL     = f"sqlite:///{DB_PATH}"

# Load order: dimensions first (FK constraint safety), then fact
LOAD_ORDER = [
    ("Dim_Date",     "Dim_Date"),
    ("Dim_Product",  "Dim_Product"),
    ("Dim_Region",   "Dim_Region"),
    ("Dim_Customer", "Dim_Customer"),
    ("Fact_Sales",   "Fact_Sales"),
]

print("=" * 65)
print("PHASE 5a — Load to SQLite Star Schema")
print("=" * 65)

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — Create / recreate the database schema via DDL
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n[1/3] Applying DDL from {DDL_FILE} → {DB_PATH} ...")

ddl_sql = DDL_FILE.read_text(encoding="utf-8")

# Use native sqlite3 to run the full DDL (executescript handles multi-statement)
with sqlite3.connect(DB_PATH) as conn:
    conn.executescript(ddl_sql)

print("      Schema created (all tables + indexes).")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — Load CSVs into tables via SQLAlchemy + pandas
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n[2/3] Loading CSVs into SQLite ...")
print("-" * 65)

engine = create_engine(DB_URL)

# Enable FK enforcement for this session
with engine.connect() as conn:
    conn.execute(text("PRAGMA foreign_keys = ON"))

csv_row_counts = {}

for csv_name, table_name in LOAD_ORDER:
    csv_path = PROCESSED / f"{csv_name}.csv"
    df = pd.read_csv(csv_path)

    # SQLite stores booleans as 0/1 integers
    bool_cols = df.select_dtypes(include="bool").columns
    for col in bool_cols:
        df[col] = df[col].astype(int)

    # SQLite has a hard limit of 999 bound variables per statement.
    # method="multi" batches (rows × columns) vars in one INSERT — easily
    # exceeds 999 for wide tables. Use method=None (executemany, one row at a
    # time) with a moderate chunksize to stay well within the limit.
    n_cols = len(df.columns)
    safe_chunk = max(1, min(5_000, 999 // n_cols))
    df.to_sql(
        name=table_name,
        con=engine,
        if_exists="append",
        index=False,
        chunksize=safe_chunk,
        method=None,          # executemany — one row per INSERT, SQLite-safe
    )

    csv_row_counts[table_name] = len(df)
    print(f"  ✓  {table_name:<16} {len(df):>8,} rows loaded from {csv_path.name}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — Verify row counts match CSV sources
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n[3/3] Verifying row counts in SQLite ...")
print("-" * 65)
print(f"  {'Table':<16}  {'CSV Rows':>10}  {'DB Rows':>10}  {'Match?':>8}")
print(f"  {'-'*16}  {'-'*10}  {'-'*10}  {'-'*8}")

all_match = True
with engine.connect() as conn:
    for _, table_name in LOAD_ORDER:
        db_count = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
        csv_count = csv_row_counts[table_name]
        match = "✓  OK" if db_count == csv_count else "✗  MISMATCH"
        if db_count != csv_count:
            all_match = False
        print(f"  {table_name:<16}  {csv_count:>10,}  {db_count:>10,}  {match:>8}")

print("-" * 65)

if all_match:
    print(f"\n✅  All row counts match. Database ready at: {DB_PATH}")
else:
    print(f"\n⚠️  Row count mismatches detected — check FK violations or dedup logic.")

print(f"\n  ➜  Next: run src/run_analysis_queries.py to execute SQL analysis.")
