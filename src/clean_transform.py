"""
clean_transform.py
==================
ETL — Phase 3 of the Enterprise Retail Sales & Supply Chain Analytics pipeline.

Loads raw SuperStore_Orders.csv and reshapes it into five star-schema tables:
    Dim_Date, Dim_Product, Dim_Region, Dim_Customer, Fact_Sales

Key design decisions documented inline:
  - Date surrogate key: integer YYYYMMDD (fast joins, human-readable, Power BI friendly)
  - Product surrogate key: numeric integer (source product_id kept as source_product_id)
  - Dim_Date is built as a CONTINUOUS calendar (no gaps) — required for Power BI's
    "Mark as Date Table" and for DAX time-intelligence functions (DATESINPERIOD,
    SAMEPERIODLASTYEAR) to work correctly.
  - returned_flag is SYNTHETIC — see note at synthesis step.
  - supplier is SYNTHETIC — see note at Dim_Product build step.
  - signup_date is APPROXIMATED — see note at Dim_Customer build step.

Output: data/processed/ — one CSV per table.
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path

# Force UTF-8 output on Windows so Unicode characters (arrows, checkmarks)
# don't cause UnicodeEncodeError in the Windows cp1252 console
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# ── Configuration ─────────────────────────────────────────────────────────────
RAW_FILE  = Path("data/raw/SuperStore_Orders.csv")
PROCESSED = Path("data/processed")
PROCESSED.mkdir(parents=True, exist_ok=True)

RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — Load raw CSV
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 65)
print("PHASE 3 — Clean & Transform")
print("=" * 65)
print(f"\n[1/7] Loading raw file: {RAW_FILE}")

df = pd.read_csv(RAW_FILE, encoding="latin-1")
print(f"      Raw rows loaded : {len(df):,}")
print(f"      Raw columns     : {list(df.columns)}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — Fix data types
# ─────────────────────────────────────────────────────────────────────────────
print("\n[2/7] Fixing data types...")

# `sales` column is stored as STRING in this dataset — must cast before math
df["sales"]    = pd.to_numeric(df["sales"],    errors="coerce")
df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
df["discount"] = pd.to_numeric(df["discount"], errors="coerce")
df["profit"]   = pd.to_numeric(df["profit"],   errors="coerce")

# Dates: format is DD-MM-YYYY (dayfirst=True required)
df["order_date"] = pd.to_datetime(df["order_date"], dayfirst=True, errors="coerce")
df["ship_date"]  = pd.to_datetime(df["ship_date"],  dayfirst=True, errors="coerce")

# Drop rows where critical fields failed to parse
rows_before = len(df)
df.dropna(subset=["sales", "order_date", "quantity", "discount", "profit"], inplace=True)
rows_dropped = rows_before - len(df)
print(f"      Rows after type-fix / null-drop : {len(df):,}  (dropped {rows_dropped:,})")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — Derive financial fields
# ─────────────────────────────────────────────────────────────────────────────
print("\n[3/7] Deriving financial fields...")

# In Superstore, `sales` = net revenue (already post-discount).
# Recover gross_revenue (pre-discount list price):
#   gross = net / (1 - discount)   when discount < 1.0
df["gross_revenue"] = np.where(
    df["discount"] < 1.0,
    df["sales"] / (1.0 - df["discount"]),
    df["sales"],                           # edge case: 100% discount
)
df["net_revenue"] = df["sales"]            # rename alias for schema clarity

# cost = revenue - profit  (Superstore does not provide cost directly)
df["cost"] = df["net_revenue"] - df["profit"]

# unit_price = pre-discount price per unit
df["unit_price"] = df["gross_revenue"] / df["quantity"]

# margin_pct = profit / net_revenue  (guard divide-by-zero)
df["margin_pct"] = np.where(
    df["net_revenue"] != 0,
    df["profit"] / df["net_revenue"],
    0.0,
)

print(f"      net_revenue  — min: {df['net_revenue'].min():.2f}  "
      f"max: {df['net_revenue'].max():.2f}")
print(f"      profit       — min: {df['profit'].min():.2f}  "
      f"max: {df['profit'].max():.2f}")
print(f"      margin_pct   — min: {df['margin_pct'].min():.3f}  "
      f"max: {df['margin_pct'].max():.3f}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — Synthesize returned_flag
# ─────────────────────────────────────────────────────────────────────────────
# ⚠️  SYNTHETIC FIELD — IMPORTANT NOTE:
#   The source SuperStore_Orders.csv does NOT contain a returns column.
#   returned_flag is generated here using a pseudorandom Bernoulli draw with
#   p=0.04 (~4% True rate) and a fixed random seed (42) for reproducibility.
#   This field is NOT derived from real return transaction data.
#   It exists solely to enable the Return Rate DAX measure and the
#   Underperformer Flag logic defined in Section 4, Stage 5 of the spec.
#   Any interview question about the return data should be answered as:
#   "The returned_flag was synthesized at ~4% to support the DAX Return Rate
#    measure; actual returns data was not available in the source dataset."
print("\n[4/7] Synthesizing returned_flag (SYNTHETIC — not from source data)...")

df["returned_flag"] = np.random.random(len(df)) < 0.04
actual_rate = df["returned_flag"].mean() * 100
print(f"      Synthesized return rate : {actual_rate:.2f}%  "
      f"({df['returned_flag'].sum():,} rows flagged True)")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — Deduplicate
# ─────────────────────────────────────────────────────────────────────────────
print("\n[5/7] Deduplicating order lines...")

rows_before = len(df)
df.drop_duplicates(
    subset=["order_id", "product_id", "order_date", "customer_name"],
    keep="first",
    inplace=True,
)
df.reset_index(drop=True, inplace=True)
print(f"      Rows after dedup : {len(df):,}  (removed {rows_before - len(df):,} dupes)")

# ═════════════════════════════════════════════════════════════════════════════
# STEP 6 — Build Dimension Tables
# ═════════════════════════════════════════════════════════════════════════════
print("\n[6/7] Building dimension tables...")

# ── Dim_Date ──────────────────────────────────────────────────────────────────
# Built as a CONTINUOUS calendar (pd.date_range, no gaps).
# This is a hard requirement for Power BI's Mark as Date Table and for DAX
# time-intelligence functions (DATESINPERIOD, SAMEPERIODLASTYEAR) to resolve
# correctly. A date table with gaps causes these functions to silently return
# wrong results.
date_min = df["order_date"].min()
date_max = df["order_date"].max()
all_dates = pd.date_range(start=date_min, end=date_max, freq="D")

dim_date = pd.DataFrame({"full_date": all_dates})
dim_date["date_id"]      = dim_date["full_date"].dt.strftime("%Y%m%d").astype(int)
dim_date["year"]         = dim_date["full_date"].dt.year
dim_date["quarter"]      = dim_date["full_date"].dt.quarter
dim_date["month"]        = dim_date["full_date"].dt.month
dim_date["month_name"]   = dim_date["full_date"].dt.strftime("%B")
dim_date["week_of_year"] = dim_date["full_date"].dt.isocalendar().week.astype(int)
dim_date["day_of_week"]  = dim_date["full_date"].dt.dayofweek   # Mon=0, Sun=6
dim_date["day_name"]     = dim_date["full_date"].dt.strftime("%A")
dim_date["is_weekend"]   = (dim_date["day_of_week"] >= 5)
# Fiscal year: Apr–Mar (common retail fiscal calendar)
dim_date["fiscal_year"]  = np.where(
    dim_date["month"] >= 4, dim_date["year"], dim_date["year"] - 1
)
dim_date = dim_date[[
    "date_id", "full_date", "year", "quarter", "month", "month_name",
    "week_of_year", "day_of_week", "day_name", "is_weekend", "fiscal_year",
]]
print(f"  Dim_Date     : {len(dim_date):>7,} rows  "
      f"({date_min.date()} → {date_max.date()}, continuous)")

# ── Dim_Product ───────────────────────────────────────────────────────────────
# Includes BOTH category (3 values) and sub_category (17 values) to represent
# the genuine hierarchical product taxonomy (3 categories / 17 sub-categories).
#
# ⚠️  supplier is SYNTHETIC — source data has no supplier column.
#     Values are assigned deterministically per sub_category using the map
#     below. This is noted here so it can be disclosed accurately in interviews
#     or the README methodology section.
SUPPLIER_MAP = {
    "Accessories" : "TechEdge Supplies",
    "Appliances"  : "HomeCore Industries",
    "Art"         : "CreativeHub Ltd",
    "Binders"     : "OfficeOne Corp",
    "Bookcases"   : "WoodCraft Furnishings",
    "Chairs"      : "ErgoComfort Inc",
    "Copiers"     : "PrintTech Solutions",
    "Envelopes"   : "MailReady Co",
    "Fasteners"   : "OfficeOne Corp",
    "Furnishings" : "WoodCraft Furnishings",
    "Labels"      : "TagMaster Ltd",
    "Machines"    : "PrintTech Solutions",
    "Paper"       : "PaperWorld Inc",
    "Phones"      : "TechEdge Supplies",
    "Storage"     : "StoreSmart Corp",
    "Supplies"    : "OfficeOne Corp",
    "Tables"      : "WoodCraft Furnishings",
}

# Mean unit cost per source product_id (cost varies by transaction so we take
# the mean across all line items for that product as a representative value)
product_unit_cost = (
    df.assign(unit_cost=df["cost"] / df["quantity"])
    .groupby("product_id")["unit_cost"]
    .mean()
    .reset_index()
)

dim_product = (
    df[["product_id", "product_name", "category", "sub_category"]]
    .drop_duplicates(subset=["product_id"])
    .sort_values("product_id")
    .reset_index(drop=True)
    .merge(product_unit_cost, on="product_id", how="left")
)
dim_product["supplier"] = dim_product["sub_category"].map(SUPPLIER_MAP)

# Numeric surrogate key (PK for star schema joins); keep original string ID
# as source_product_id for traceability
dim_product.insert(0, "product_key", range(1, len(dim_product) + 1))
dim_product = dim_product.rename(columns={"product_id": "source_product_id"})
dim_product = dim_product[[
    "product_key", "source_product_id", "product_name",
    "category", "sub_category", "unit_cost", "supplier",
]]

# Lookup: source_product_id → numeric product_key (for FK in Fact_Sales)
product_key_map = dict(
    zip(dim_product["source_product_id"], dim_product["product_key"])
)

print(f"  Dim_Product  : {len(dim_product):>7,} rows  "
      f"(categories={dim_product['category'].nunique()}, "
      f"sub_categories={dim_product['sub_category'].nunique()})")

# ── Dim_Region ────────────────────────────────────────────────────────────────
# Source dataset is global with 13 distinct region values (not US-only 4).
# Dim_Region is built at the region level; market is included as a parent
# grouping attribute (7 markets). country is omitted — it is many-to-one
# with region (many countries per region) and does not fit a dimension row.
dim_region = (
    df[["region", "market"]]
    .drop_duplicates(subset=["region"])
    .sort_values("region")
    .reset_index(drop=True)
)
dim_region.insert(0, "region_id", range(1, len(dim_region) + 1))
dim_region["warehouse_id"] = ["WH-" + str(i).zfill(3) for i in dim_region["region_id"]]
dim_region = dim_region.rename(columns={"region": "region_name"})[
    ["region_id", "region_name", "market", "warehouse_id"]
]

region_id_map = dict(zip(dim_region["region_name"], dim_region["region_id"]))
print(f"  Dim_Region   : {len(dim_region):>7,} rows  "
      f"(regions={dim_region['region_name'].nunique()}, "
      f"markets={dim_region['market'].nunique()})")

# ── Dim_Customer ──────────────────────────────────────────────────────────────
# Source has customer_name + segment; no customer_id or signup_date.
# Surrogate customer_id generated as sequential integer.
#
# ⚠️  signup_date is APPROXIMATED as the customer's earliest order_date in the
#     dataset. The source does not contain an explicit signup/registration date.
dim_customer = (
    df[["customer_name", "segment", "order_date"]]
    .rename(columns={"segment": "customer_segment", "order_date": "signup_date"})
    .sort_values("signup_date")
    .drop_duplicates(subset=["customer_name", "customer_segment"], keep="first")
    .reset_index(drop=True)
)
dim_customer.insert(0, "customer_id", range(1, len(dim_customer) + 1))
dim_customer = dim_customer[[
    "customer_id", "customer_name", "customer_segment", "signup_date"
]]

customer_id_map = dict(
    zip(
        zip(dim_customer["customer_name"], dim_customer["customer_segment"]),
        dim_customer["customer_id"],
    )
)
print(f"  Dim_Customer : {len(dim_customer):>7,} rows  "
      f"(segments={dim_customer['customer_segment'].nunique()})")

# ═════════════════════════════════════════════════════════════════════════════
# Build Fact_Sales
# ═════════════════════════════════════════════════════════════════════════════
print("  Building Fact_Sales (attaching FK surrogate keys)...")

fact = df.copy()

# Attach FK surrogate keys
fact["date_id"]     = fact["order_date"].dt.strftime("%Y%m%d").astype(int)
fact["product_id"]  = fact["product_id"].map(product_key_map)
fact["region_id"]   = fact["region"].map(region_id_map)
fact["customer_id"] = [
    customer_id_map.get((row["customer_name"], row["segment"]))
    for _, row in fact.iterrows()
]

# Sequential PK
fact.reset_index(drop=True, inplace=True)
fact.insert(0, "sales_id", range(1, len(fact) + 1))

fact_sales = fact[[
    "sales_id", "order_id", "date_id", "product_id", "region_id", "customer_id",
    "quantity", "unit_price", "discount", "gross_revenue", "net_revenue",
    "cost", "profit", "margin_pct", "returned_flag",
    "shipping_cost", "ship_mode", "order_priority",
]].rename(columns={"discount": "discount_pct"})

# Verify no FK nulls crept in
fk_nulls = fact_sales[["date_id","product_id","region_id","customer_id"]].isnull().sum()
if fk_nulls.any():
    print(f"  ⚠️  FK null counts:\n{fk_nulls[fk_nulls > 0]}")
else:
    print("      All FK joins resolved — no nulls.")

print(f"  Fact_Sales   : {len(fact_sales):>7,} rows")

# ═════════════════════════════════════════════════════════════════════════════
# STEP 7 — Save to data/processed/
# ═════════════════════════════════════════════════════════════════════════════
print("\n[7/7] Saving star-schema CSVs to data/processed/ ...")
print("-" * 65)

tables = {
    "Dim_Date"    : dim_date,
    "Dim_Product" : dim_product,
    "Dim_Region"  : dim_region,
    "Dim_Customer": dim_customer,
    "Fact_Sales"  : fact_sales,
}

for name, table in tables.items():
    out_path = PROCESSED / f"{name}.csv"
    table.to_csv(out_path, index=False)
    print(f"  ✓  {name:<16} {len(table):>7,} rows   →  {out_path}")

print("-" * 65)
print("\n✅  ETL complete. Five star-schema CSVs ready in data/processed/")
print(f"    Date range  : {date_min.date()}  →  {date_max.date()}")
print(f"    Categories  : {dim_product['category'].nunique()} "
      f"({', '.join(sorted(dim_product['category'].unique()))})")
print(f"    Sub-cats    : {dim_product['sub_category'].nunique()}")
print(f"    Regions     : {dim_region['region_name'].nunique()}")
print(f"    Markets     : {dim_region['market'].nunique()}")
print(f"    Customers   : {len(dim_customer):,}")
print(f"    Fact rows   : {len(fact_sales):,}")
print()
print("  ➜  Next: run src/augment_data.py to scale Fact_Sales to 100K+ rows")
print("           and inject the underperforming segment bias.")
