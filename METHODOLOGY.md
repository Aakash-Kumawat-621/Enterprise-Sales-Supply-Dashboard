# METHODOLOGY.md
## Data Methodology & Design Decisions

This document records every decision that deviated from "pure real data" so that
the project can be defended accurately in interviews or code reviews.  
Last updated: Phase 3 (ETL complete) — will be updated after Phase 4 (augmentation).

---

## 1. Source Data

| Item | Detail |
|---|---|
| **Dataset** | Kaggle Superstore Orders (`SuperStore_Orders.csv`) |
| **Source** | `vivek468/superstore-dataset-final` (public, free) |
| **Raw rows** | 51,290 |
| **Date range** | 2011-01-01 → 2014-12-31 |
| **Geographic scope** | Global (7 markets, 13 regions) |

---

## 2. Data Cleaning Decisions (Phase 3 — `src/clean_transform.py`)

### 2.1 `sales` column stored as string
- **Issue**: The `sales` column in the raw CSV is dtype `object` (string), not numeric.
- **Fix**: `pd.to_numeric(df["sales"], errors="coerce")` — coerced non-numeric values to NaN, then dropped them.
- **Impact**: 2,630 rows dropped (could not parse; likely corrupt or formatted differently).

### 2.2 Date format `DD-MM-YYYY`
- **Issue**: Dates stored as `DD-MM-YYYY` strings, not ISO 8601.
- **Fix**: `pd.to_datetime(..., dayfirst=True)` to prevent day/month swap.

### 2.3 Deduplication
- **31 exact duplicate rows** removed (same `order_id + product_id + order_date + customer_name`).

### 2.4 `gross_revenue` derivation
- The source `sales` column is **net revenue** (post-discount, as confirmed by the Superstore schema docs).
- `gross_revenue = net_revenue / (1 - discount_pct)` used to recover pre-discount list price.
- Edge case: if `discount_pct == 1.0`, `gross_revenue = net_revenue` (avoids divide-by-zero).

### 2.5 `cost` derivation
- Source dataset does not expose a cost column directly.
- `cost = net_revenue - profit` (algebraically exact given the Superstore schema).

### 2.6 `unit_price` in `Dim_Product`
- Stored as **mean unit cost across all transactions** for that product.
- Varies slightly per transaction due to discount; mean is used as the representative value.

---

## 3. Synthetic / Approximated Fields

### 3.1 `returned_flag` ⚠️ SYNTHETIC
- **The source dataset has NO returns column.**
- `returned_flag` is generated using a pseudorandom Bernoulli draw (`p = 0.04`, seed = 42).
- Actual return rate produced: **~3.92%** (1,906 rows out of 48,629).
- **Interview answer**: *"The returned_flag was synthesised at ~4% True to support the Return Rate DAX measure. Actual returns data was not available in the source dataset. The random seed is fixed at 42 so results are fully reproducible."*

### 3.2 `supplier` in `Dim_Product` ⚠️ SYNTHETIC
- Source has no supplier column.
- Deterministically assigned per `sub_category` using a hardcoded mapping (e.g., Chairs → ErgoComfort Inc, Phones → TechEdge Supplies).
- 6 unique synthetic suppliers across 17 sub-categories.

### 3.3 `signup_date` in `Dim_Customer` ⚠️ APPROXIMATED
- Source has no explicit customer registration date.
- Approximated as the customer's **earliest order_date** in the dataset.
- This under-estimates true tenure for customers active before 2011.

---

## 4. Augmentation (Phase 4 — `src/augment_data.py`)

Augmentation completed successfully. All numbers below are from the actual run output.

| Metric | Value |
|---|---|
| Original Fact_Sales rows | 48,629 |
| Rows added (resampled with replacement) | 51,371 |
| **Final Fact_Sales rows** | **100,000** |
| Dim_Date range | 2011-01-01 → 2014-12-31 (unchanged, continuous) |
| Dim_Date rows | 1,461 (no gaps — verified) |

### Underperforming Segment Injected

| Field | Value |
|---|---|
| **Region** | South |
| **Category** | Furniture |
| **Sub-Category** | Tables |
| Rows in segment | 207 |
| `discount_pct` forced to | 40% – 60% (mean: 50.1%) |
| `margin_pct` forced to | −20% to −5% (mean: −12.2%) |
| `returned_flag` rate | 21.3% (baseline: ~4%) |
| Total segment profit | **−$11,165.24** (negative as intended) |

**Interview answer for "what did you find?"**:  
*"Furniture → Tables in the South region showed a mean margin of −12.2%, a return rate of 21.3% vs a 4% dataset baseline, and an average discount of 50% — the clear worst-performing segment. The SQL cross-validation query in `sql/analysis_queries.sql` independently confirms these numbers without DAX."*

---

## 5. Star Schema Design Decisions

### 5.1 Why star schema over flat table?
A single wide table works for small demos but breaks down at scale and with multiple
dimensions. The star schema keeps `Fact_Sales` lean (mostly FKs + numeric measures),
which is required for DAX aggregations to perform correctly. More critically,
**DAX time-intelligence functions (`DATESINPERIOD`, `SAMEPERIODLASTYEAR`) require
a proper marked Date dimension table** — they silently return wrong results when
the date column lives inside a flat fact table.

### 5.2 Why `Dim_Date` must be continuous?
Power BI's "Mark as Date Table" validation rejects a date table with gaps.
DAX functions like `SAMEPERIODLASTYEAR` generate a date set internally; if the
date table has gaps, those generated dates have no match and the measure returns
BLANK instead of the correct prior-year value.
`Dim_Date` is built with `pd.date_range(freq="D")` — guaranteed continuous.

### 5.3 Why SQLite (not PostgreSQL) for local development?
Zero install, zero server setup, portable single-file database.
The SQL DDL, FK constraints, and analysis queries are all standard SQL — swapping
to PostgreSQL for production (e.g., Supabase free tier) requires only changing the
SQLAlchemy connection string, not the query logic.

### 5.4 Product taxonomy: 3 categories / 17 sub-categories
The original spec assumed "5+ categories". The real Superstore dataset has 3 top-level
categories but 17 sub-categories — a richer hierarchical taxonomy. `Dim_Product`
exposes **both** `category` and `sub_category` columns so Power BI can drill from
category → sub-category in all visuals.

---

## 6. Reproducibility

| Item | Value |
|---|---|
| Random seed (all scripts) | `42` |
| Python version | 3.11+ |
| Key library versions | See `requirements.txt` |
| Raw data SHA-256 | *(run `certutil -hashfile data/raw/SuperStore_Orders.csv SHA256` and paste here)* |
