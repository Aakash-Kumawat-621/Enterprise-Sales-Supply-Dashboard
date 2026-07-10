"""
augment_data.py
===============
ETL — Phase 4 of the Enterprise Retail Sales & Supply Chain Analytics pipeline.

Scales Fact_Sales from ~48K rows to 100,000+ rows via row resampling with
realistic jitter, then deliberately biases one specific region × sub_category
combination to serve as the "underperforming segment" the project identifies.

Underperforming segment planted:
    Region     : South
    Category   : Furniture
    Sub-category: Tables

    Bias applied (documented for METHODOLOGY.md and interview prep):
        - discount_pct   boosted to 0.40–0.60  (vs ~0.15 dataset mean)
        - returned_flag  set True at 25% rate   (vs ~4% baseline)
        - margin_pct     forced negative (−0.05 to −0.20)
        - net_revenue    reduced accordingly (cost held, profit = net − cost < 0)

    Rationale: Tables in the South region is the largest furniture sub-category
    with the most supplier variability, making a "over-discounted, high-return,
    negative-margin" narrative credible and specific enough to be interview-ready.

Also updates Dim_Date to remain continuous across the extended date range.

Console log is structured as documentation — treat it as the methodology log
referenced in README.md and METHODOLOGY.md.
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# ── Configuration ─────────────────────────────────────────────────────────────
PROCESSED   = Path("data/processed")
TARGET_ROWS = 100_000          # minimum fact rows after augmentation
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

# ── Underperformer definition (hardcoded — see module docstring) ──────────────
UNDERPERFORM_REGION      = "South"
UNDERPERFORM_CATEGORY    = "Furniture"
UNDERPERFORM_SUBCATEGORY = "Tables"   # most specific — single sub-category
UNDERPERFORM_RETURN_RATE = 0.25       # 25% returns (vs ~4% baseline)
UNDERPERFORM_DISCOUNT_LO = 0.40       # discount range: 40–60%
UNDERPERFORM_DISCOUNT_HI = 0.60
UNDERPERFORM_MARGIN_LO   = -0.20      # margin range: −20% to −5%
UNDERPERFORM_MARGIN_HI   = -0.05

print("=" * 65)
print("PHASE 4 — Augment to 100K+ rows + Inject Underperforming Segment")
print("=" * 65)

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — Load processed tables
# ─────────────────────────────────────────────────────────────────────────────
print("\n[1/6] Loading star-schema tables from data/processed/ ...")

fact      = pd.read_csv(PROCESSED / "Fact_Sales.csv")
dim_date  = pd.read_csv(PROCESSED / "Dim_Date.csv")
dim_prod  = pd.read_csv(PROCESSED / "Dim_Product.csv")
dim_reg   = pd.read_csv(PROCESSED / "Dim_Region.csv")
dim_cust  = pd.read_csv(PROCESSED / "Dim_Customer.csv")

original_rows = len(fact)
print(f"      Fact_Sales original row count : {original_rows:,}")

# Parse date column for later use
dim_date["full_date"] = pd.to_datetime(dim_date["full_date"])

# Build lookup: product_key → sub_category and region_id → region_name
product_meta = dim_prod.set_index("product_key")[["category", "sub_category"]]
region_meta  = dim_reg.set_index("region_id")["region_name"]

# Tag each fact row with category, sub_category, region_name for bias logic
fact = fact.join(product_meta,    on="product_id")
fact = fact.join(region_meta,     on="region_id")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — Resample to reach TARGET_ROWS
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n[2/6] Resampling to reach {TARGET_ROWS:,} rows ...")

rows_needed = TARGET_ROWS - original_rows
sampled = fact.sample(n=rows_needed, replace=True, random_state=RANDOM_SEED).copy()

print(f"      Rows sampled (with replacement): {len(sampled):,}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — Jitter numeric fields on resampled rows
# ─────────────────────────────────────────────────────────────────────────────
print("\n[3/6] Applying jitter to resampled rows ...")

n = len(sampled)

# Randomise order dates across the full 2011–2014 range
date_min = dim_date["full_date"].min()
date_max = dim_date["full_date"].max()
date_range_days = (date_max - date_min).days

random_days     = np.random.randint(0, date_range_days + 1, size=n)
new_dates       = pd.to_datetime(date_min) + pd.to_timedelta(random_days, unit="D")
sampled["order_date_jittered"] = new_dates   # temporary column for date_id rebuild

# Jitter quantity (±1, clamped to [1, 14])
qty_jitter          = np.random.randint(-1, 2, size=n)
sampled["quantity"] = (sampled["quantity"] + qty_jitter).clip(1, 14)

# Jitter discount_pct (±0–5%, clamped to [0, 0.85])
disc_jitter             = np.random.uniform(-0.05, 0.05, size=n)
sampled["discount_pct"] = (sampled["discount_pct"] + disc_jitter).clip(0.0, 0.85)

# Re-derive revenue / profit / margin with jittered values
# Approach: hold unit_price and cost ratios stable, re-compute from quantity + discount
sampled["gross_revenue"] = sampled["unit_price"] * sampled["quantity"]
sampled["net_revenue"]   = sampled["gross_revenue"] * (1.0 - sampled["discount_pct"])
# Cost: use margin structure from original row (cost = net * (1 - margin_pct))
# This preserves the original profitability signal while jittering volumes
sampled["cost"]          = sampled["net_revenue"] * (1.0 - sampled["margin_pct"].clip(-5, 0.99))
sampled["profit"]        = sampled["net_revenue"] - sampled["cost"]
sampled["margin_pct"]    = np.where(
    sampled["net_revenue"] != 0,
    sampled["profit"] / sampled["net_revenue"],
    0.0,
)

# Synthesize returned_flag for resampled rows at baseline ~4% rate
sampled["returned_flag"] = np.random.random(n) < 0.04

print(f"      Jitter applied: dates randomised, quantity ±1, discount ±5%")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — Combine original + resampled rows
# ─────────────────────────────────────────────────────────────────────────────
print("\n[4/6] Combining original + resampled rows ...")

combined = pd.concat([fact, sampled], ignore_index=True)
print(f"      Combined row count : {len(combined):,}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — Inject underperforming segment bias
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n[5/6] Injecting underperformer bias ...")
print(f"      Target : region='{UNDERPERFORM_REGION}' | "
      f"category='{UNDERPERFORM_CATEGORY}' | "
      f"sub_category='{UNDERPERFORM_SUBCATEGORY}'")

# Identify rows belonging to the underperforming segment
mask = (
    (combined["region_name"]  == UNDERPERFORM_REGION) &
    (combined["category"]      == UNDERPERFORM_CATEGORY) &
    (combined["sub_category"]  == UNDERPERFORM_SUBCATEGORY)
)
n_segment = mask.sum()
print(f"      Rows in segment before bias : {n_segment:,}")

if n_segment == 0:
    print("  ⚠️  WARNING: No rows matched underperformer criteria — check column names.")
else:
    idx = combined.index[mask]

    # -- Boost discount to 40–60% (representing aggressive, unsustainable markdowns) --
    combined.loc[idx, "discount_pct"] = np.random.uniform(
        UNDERPERFORM_DISCOUNT_LO, UNDERPERFORM_DISCOUNT_HI, size=n_segment
    )

    # -- Force negative margin (−20% to −5%) --
    target_margins = np.random.uniform(
        UNDERPERFORM_MARGIN_LO, UNDERPERFORM_MARGIN_HI, size=n_segment
    )
    combined.loc[idx, "margin_pct"] = target_margins

    # -- Recompute financials consistently with forced margin + new discount --
    combined.loc[idx, "gross_revenue"] = (
        combined.loc[idx, "unit_price"] * combined.loc[idx, "quantity"]
    )
    combined.loc[idx, "net_revenue"] = (
        combined.loc[idx, "gross_revenue"] * (1.0 - combined.loc[idx, "discount_pct"])
    )
    combined.loc[idx, "profit"] = (
        combined.loc[idx, "net_revenue"] * combined.loc[idx, "margin_pct"]
    )
    combined.loc[idx, "cost"] = (
        combined.loc[idx, "net_revenue"] - combined.loc[idx, "profit"]
    )

    # -- Boost returned_flag to 25% rate --
    combined.loc[idx, "returned_flag"] = np.random.random(n_segment) < UNDERPERFORM_RETURN_RATE

    # Verify bias was applied correctly
    seg = combined.loc[idx]
    print(f"      Bias applied:")
    print(f"        discount_pct  — mean: {seg['discount_pct'].mean():.3f}  "
          f"(target: {UNDERPERFORM_DISCOUNT_LO}–{UNDERPERFORM_DISCOUNT_HI})")
    print(f"        margin_pct    — mean: {seg['margin_pct'].mean():.3f}  "
          f"(target: {UNDERPERFORM_MARGIN_LO} to {UNDERPERFORM_MARGIN_HI})")
    print(f"        return rate   — {seg['returned_flag'].mean()*100:.1f}%  "
          f"(target: {UNDERPERFORM_RETURN_RATE*100:.0f}%)")
    print(f"        total profit  — {seg['profit'].sum():,.2f}  (expected: negative)")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — Rebuild Fact_Sales and update Dim_Date
# ─────────────────────────────────────────────────────────────────────────────
print("\n[6/6] Rebuilding Fact_Sales and saving ...")

# Rebuild date_id for jittered rows (original rows already have correct date_id)
jitter_mask = combined["order_date_jittered"].notna()
if jitter_mask.any():
    combined.loc[jitter_mask, "date_id"] = (
        pd.to_datetime(combined.loc[jitter_mask, "order_date_jittered"])
        .dt.strftime("%Y%m%d")
        .astype(int)
    )

# Drop helper columns before saving
combined.drop(
    columns=["order_date_jittered", "category", "sub_category", "region_name"],
    errors="ignore",
    inplace=True,
)

# Reassign clean sequential sales_id
combined.reset_index(drop=True, inplace=True)
combined["sales_id"] = range(1, len(combined) + 1)

# Ensure Dim_Date covers the full extended date range (continuous, no gaps)
new_date_min = dim_date["full_date"].min()
new_date_max = dim_date["full_date"].max()

all_dates = pd.date_range(start=new_date_min, end=new_date_max, freq="D")
dim_date_new = pd.DataFrame({"full_date": all_dates})
dim_date_new["date_id"]      = dim_date_new["full_date"].dt.strftime("%Y%m%d").astype(int)
dim_date_new["year"]         = dim_date_new["full_date"].dt.year
dim_date_new["quarter"]      = dim_date_new["full_date"].dt.quarter
dim_date_new["month"]        = dim_date_new["full_date"].dt.month
dim_date_new["month_name"]   = dim_date_new["full_date"].dt.strftime("%B")
dim_date_new["week_of_year"] = dim_date_new["full_date"].dt.isocalendar().week.astype(int)
dim_date_new["day_of_week"]  = dim_date_new["full_date"].dt.dayofweek
dim_date_new["day_name"]     = dim_date_new["full_date"].dt.strftime("%A")
dim_date_new["is_weekend"]   = (dim_date_new["day_of_week"] >= 5)
dim_date_new["fiscal_year"]  = np.where(
    dim_date_new["month"] >= 4, dim_date_new["year"], dim_date_new["year"] - 1
)
dim_date_new = dim_date_new[[
    "date_id", "full_date", "year", "quarter", "month", "month_name",
    "week_of_year", "day_of_week", "day_name", "is_weekend", "fiscal_year",
]]

# Save outputs
combined.to_csv(PROCESSED / "Fact_Sales.csv", index=False)
dim_date_new.to_csv(PROCESSED / "Dim_Date.csv", index=False)

# ── Final summary (treat as documentation log for METHODOLOGY.md / README) ───
print()
print("=" * 65)
print("AUGMENTATION COMPLETE — METHODOLOGY LOG")
print("=" * 65)
print(f"  Original Fact_Sales rows    : {original_rows:,}")
print(f"  Rows added (resampled)      : {rows_needed:,}")
print(f"  Final Fact_Sales rows       : {len(combined):,}")
print(f"  Dim_Date range (unchanged)  : {new_date_min.date()} → {new_date_max.date()}")
print(f"  Dim_Date rows               : {len(dim_date_new):,}  (continuous, no gaps)")
print()
print("  UNDERPERFORMING SEGMENT INJECTED:")
print(f"    Region         : {UNDERPERFORM_REGION}")
print(f"    Category       : {UNDERPERFORM_CATEGORY}")
print(f"    Sub-Category   : {UNDERPERFORM_SUBCATEGORY}")
print(f"    Rows in segment: {n_segment:,}")
print(f"    Discount range : {UNDERPERFORM_DISCOUNT_LO*100:.0f}% – {UNDERPERFORM_DISCOUNT_HI*100:.0f}%")
print(f"    Margin range   : {UNDERPERFORM_MARGIN_LO*100:.0f}% – {UNDERPERFORM_MARGIN_HI*100:.0f}%")
print(f"    Return rate    : {UNDERPERFORM_RETURN_RATE*100:.0f}%  (baseline: ~4%)")
print()
print("  Copy the above block into METHODOLOGY.md Section 4.")
print()
print("  ➜  Next: run src/load_to_db.py to load into SQLite star schema.")
