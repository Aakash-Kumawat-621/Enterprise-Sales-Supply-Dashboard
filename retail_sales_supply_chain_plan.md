# Enterprise Retail Sales & Supply Chain Analytics
### Full Build Plan & Architecture (Power BI · DAX · SQL · Python)

Target resume line this project supports:
> End-to-end analytics over 100K+ transaction records; built a Star Schema data model across 4 regions and 5+ categories with an interactive Power BI dashboard using time-intelligence DAX (rolling 30/90-day, YoY). Identified underperforming inventory segments and produced data-driven supply chain recommendations translating raw dataset complexity into actionable intelligence for business stakeholders.

This doc is written so you can execute it phase-by-phase in **Antigravity** for the Python/SQL portions, then finish the BI layer manually in Power BI Desktop (Power BI itself isn't scriptable by an agent in the same way — noted clearly in Section 6 below).

---

## 1. Problem Framing

**Business problem:** A multi-region retailer wants to understand:
1. Which **regions and categories** are driving vs. dragging revenue?
2. What's the **trend** (rolling 30/90-day, Year-over-Year) — not just a snapshot?
3. Which **inventory segments are underperforming** (slow-moving stock, high returns, low margin) and what should supply chain do about it (reorder less, discount, discontinue, reallocate across regions)?

**Why Star Schema (not a flat table) — the core technical thesis:**
- A single wide "everything" table works for small demos but breaks down with real transaction volume and multiple dimensions (region, category, time, customer).
- A **Star Schema** — one central `Fact_Sales` table + surrounding dimension tables (`Dim_Date`, `Dim_Product`, `Dim_Region`, `Dim_Customer`) — is the standard BI data-modeling pattern because it:
  - Keeps fact rows lean (mostly foreign keys + numeric measures), so DAX aggregations are fast even at scale.
  - Lets DAX time-intelligence functions (`DATESINPERIOD`, `SAMEPERIODLASTYEAR`) work correctly, which **require a proper marked Date dimension table** — this is a hard technical requirement you should be ready to explain.
  - Avoids duplicated attributes across rows (normalization), reducing model size and improving refresh performance.
- This is the exact narrative to have ready for interviews: "I modeled it as a star schema specifically because DAX time-intelligence functions need a continuous, marked date table to work correctly, and flat tables cause context-transition bugs in measures."

---

## 2. Data Layer

### 2.1 Data source options

| Option | Description | Effort |
|---|---|---|
| **A. Kaggle retail dataset** | e.g., "Superstore Sales" (public, ~10K rows) or "Online Retail II" (UCI, ~1M rows, UK e-commerce) — scale/sample to 100K+ | Low |
| B. Synthetic generator | Simulate a retailer with `faker` + weighted random sampling across 4 regions, 5+ categories, seasonal patterns, and deliberately-planted underperforming segments | Medium — best if you want the "4 regions / 5+ categories" numbers to match exactly |
| C. Combine both | Use a real dataset as the backbone, then synthetically extend/duplicate-with-noise to hit 100K+ rows across your exact region/category structure | Medium |

**Recommendation:** Use a **synthetic generator** as the primary source. Reasons:
- You control region count (exactly 4), category count (exactly 5+), and row count (100K+) to match your resume claim precisely, reproducibly.
- You can deliberately plant "underperforming inventory segments" (e.g., one category in one region with high returns + low turnover) — this makes your "identified underperforming segments" bullet a genuine finding rather than a vague claim, since you'll know the answer exists and can validate your analysis found it.
- Still cite that the schema/realism is modeled on public retail datasets (Superstore/Online Retail II) for credibility if asked.

### 2.2 Schema (target — this becomes your Star Schema)

**Fact_Sales** (grain: one row per order line item)
```
sales_id (PK)
order_id
date_id (FK → Dim_Date)
product_id (FK → Dim_Product)
region_id (FK → Dim_Region)
customer_id (FK → Dim_Customer)
quantity
unit_price
discount_pct
gross_revenue
net_revenue
cost
profit
returned_flag
```

**Dim_Date** (continuous calendar table — critical for DAX time-intelligence)
```
date_id (PK)
full_date
year, quarter, month, month_name
week_of_year, day_of_week
is_weekend
fiscal_year (optional)
```

**Dim_Product**
```
product_id (PK)
product_name
category        # 5+ categories
sub_category
unit_cost
supplier
```

**Dim_Region**
```
region_id (PK)
region_name      # 4 regions, e.g., North, South, East, West
country / state
warehouse_id
```

**Dim_Customer**
```
customer_id (PK)
customer_segment   # e.g., Consumer, Corporate, Small Business
signup_date
```

### 2.3 Data volume plan
- Generate/aggregate to **100,000+ fact rows** minimum.
- Spread across **4 regions**, **5+ categories** (e.g., Electronics, Furniture, Apparel, Grocery, Office Supplies), 2–3 years of dates (needed for YoY comparisons to make sense).
- Deliberately inject 1–2 "underperforming segments" (e.g., Furniture in South region: high return rate + negative margin) so your analysis has a real finding to report.

---

## 3. High-Level System Architecture

```
                ┌───────────────────────────────────┐
                │  Data Generation / Source Data      │
                │  (Python: faker + pandas, or         │
                │   Kaggle CSV as backbone)            │
                └───────────────────┬─────────────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │ 1. Python ETL: Clean & Shape     │
                    │  (pandas — dedupe, types,        │
                    │   derive profit/margin fields)   │
                    └───────────────┬───────────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │ 2. SQL Layer                     │
                    │  (load into PostgreSQL/SQLite,   │
                    │   build star schema tables via   │
                    │   SQL DDL + FK constraints)      │
                    └───────────────┬───────────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │ 3. SQL Analysis Queries          │
                    │  (region/category rollups,       │
                    │   underperformer detection,      │
                    │   window functions for trends)   │
                    └───────────────┬───────────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │ 4. Power BI — Data Model          │
                    │  (import/DirectQuery star schema, │
                    │   relationships, mark Date table) │
                    └───────────────┬───────────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │ 5. DAX Measures Layer              │
                    │  (rolling 30/90-day, YoY,          │
                    │   margin %, underperformer flags)  │
                    └───────────────┬───────────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │ 6. Power BI Report / Dashboard     │
                    │  (exec summary, region drill-down, │
                    │   inventory health, recommendations)│
                    └───────────────────────────────────┘
```

---

## 4. Pipeline Stage Details

### Stage 1 — Python ETL: Data Generation & Cleaning
- Generate or load transaction-level data.
- Clean: handle nulls, fix data types (dates as datetime, prices as float), dedupe order lines.
- Derive fields: `net_revenue = quantity * unit_price * (1 - discount_pct)`, `profit = net_revenue - cost`, `margin_pct = profit / net_revenue`.
- Deliberately inject the underperforming segment(s) with realistic bad numbers (high discount + high return rate + thin/negative margin) so later analysis has something concrete to surface.
- Output: clean CSV/Parquet files, one per proposed dimension/fact table (already shaped toward the star schema).

### Stage 2 — SQL Layer: Star Schema Build
- Spin up **PostgreSQL** (or SQLite for simplicity if you want zero-install) locally.
- Write DDL scripts to create `Fact_Sales`, `Dim_Date`, `Dim_Product`, `Dim_Region`, `Dim_Customer` with proper primary/foreign keys.
- Load the cleaned Python output into these tables (via `psycopg2`/`SQLAlchemy` or `sqlite3` + pandas `.to_sql()`).
- This SQL layer is what justifies the "SQL" tag in your resume tech stack — it's not just Power BI's internal model, it's a real relational database you built and queried.

### Stage 3 — SQL Analysis Queries (pre-BI validation)
Write and save (in `sql/analysis_queries.sql`) a set of exploratory queries, e.g.:
- Revenue by region and category (`GROUP BY` + `SUM`)
- Month-over-month revenue trend (`window functions`: `LAG()`, `SUM() OVER (ORDER BY ...)`)
- Return rate and margin by category × region (to identify underperformers *before* you build DAX — validates your BI findings against raw SQL, which is a strong interview point: "I cross-validated my Power BI findings against raw SQL aggregation to make sure the DAX measures were correct.")
- Top/bottom 10 products by profit margin.

### Stage 4 — Power BI Data Model
*(Manual step in Power BI Desktop — Antigravity can generate the SQL/CSV inputs and even DAX text, but you'll import/wire the model yourself in the Power BI UI.)*
- Import the star schema tables (via SQL connector or CSV import).
- Set up relationships: `Fact_Sales[date_id] → Dim_Date[date_id]` (one-to-many), similarly for product/region/customer.
- **Mark `Dim_Date` as the official Date Table** (Power BI: Table tools → Mark as Date Table) — required for time-intelligence DAX to work.
- Hide foreign key columns in Fact_Sales from report view (BI modeling best practice — keeps the field list clean for report builders).
- Set proper data types and formatting (currency for revenue/profit fields, percentage for margin/discount).

### Stage 5 — DAX Measures Layer
Core measures to build (write these as a documented list — you'll paste them into Power BI):
```dax
Total Revenue = SUM(Fact_Sales[net_revenue])

Total Profit = SUM(Fact_Sales[profit])

Margin % = DIVIDE([Total Profit], [Total Revenue], 0)

Rolling 30-Day Revenue = 
CALCULATE(
    [Total Revenue],
    DATESINPERIOD(Dim_Date[full_date], MAX(Dim_Date[full_date]), -30, DAY)
)

Rolling 90-Day Revenue = 
CALCULATE(
    [Total Revenue],
    DATESINPERIOD(Dim_Date[full_date], MAX(Dim_Date[full_date]), -90, DAY)
)

Revenue YoY = 
VAR CurrentRev = [Total Revenue]
VAR PriorYearRev = 
    CALCULATE([Total Revenue], SAMEPERIODLASTYEAR(Dim_Date[full_date]))
RETURN 
    DIVIDE(CurrentRev - PriorYearRev, PriorYearRev, 0)

Return Rate = 
DIVIDE(
    CALCULATE(COUNTROWS(Fact_Sales), Fact_Sales[returned_flag] = TRUE),
    COUNTROWS(Fact_Sales),
    0
)

Underperformer Flag = 
IF([Margin %] < 0.05 && [Return Rate] > 0.15, "Underperforming", "Healthy")
```
- These directly back up "time-intelligence DAX (rolling 30/90-day, YoY)" and the underperformer-identification claim in your resume bullet.

### Stage 6 — Power BI Report Pages
Build 3–4 report pages:
1. **Executive Summary** — KPI cards (Total Revenue, Profit, Margin %, YoY Growth), trend line chart with rolling 30/90-day overlay.
2. **Region Deep-Dive** — map or bar chart by region, category breakdown per region, drill-through to product level.
3. **Inventory Health** — table of products/categories flagged as "Underperforming" via the DAX measure, sorted by lowest margin / highest return rate, conditional formatting (red/yellow/green).
4. **Recommendations** — a text/callout page (or tooltip annotations) summarizing the 2–3 concrete supply-chain actions your analysis supports (e.g., "reduce reorder volume for Furniture in South region by X%, given Y% return rate and negative margin").

---

## 5. Tech Stack Summary

| Layer | Tool |
|---|---|
| Data generation/cleaning | Python (pandas, faker, numpy) |
| Database | PostgreSQL (or SQLite for simplicity) |
| SQL analysis | Raw SQL (window functions, aggregations) |
| BI modeling | Power BI Desktop — star schema, relationships |
| Measures | DAX |
| Version control | Git (track .sql, .py, .pbix — note .pbix is binary, so document changes in README instead of relying on diffs) |

---

## 6. Important note on Antigravity's role here

Unlike the DBSCAN project, **Power BI Desktop itself cannot be driven by an AI coding agent** the way Python/SQL scripts can — there's no scriptable API for building visuals or wiring the data model in the desktop app. So the split is:

- **Antigravity does:** Stage 1 (Python data generation/ETL), Stage 2 (SQL DDL + load scripts), Stage 3 (SQL analysis queries), and can **write out the exact DAX text** for Stage 5 as a reference file for you to paste in.
- **You do manually in Power BI Desktop:** import the data, wire relationships, mark the date table, paste in the DAX measures, and build the report visuals (Stages 4 and 6).

This is worth knowing upfront so you don't expect the agent to "build the dashboard" end-to-end.

---

## 7. Repository Structure

```
retail-sales-supply-chain-analytics/
├── data/
│   ├── raw/                      # generated or source CSVs
│   └── processed/                 # cleaned, star-schema-shaped CSVs
├── sql/
│   ├── ddl_create_star_schema.sql
│   ├── load_data.sql (or python loader script)
│   └── analysis_queries.sql
├── src/
│   ├── generate_data.py           # synthetic data generator
│   ├── clean_transform.py         # pandas ETL
│   └── load_to_db.py              # loads processed data into PostgreSQL/SQLite
├── dax/
│   └── measures.dax               # documented DAX measures (Stage 5 text)
├── powerbi/
│   └── retail_dashboard.pbix       # the actual Power BI file (built manually)
├── notebooks/
│   └── eda.ipynb                   # exploratory analysis, sanity-check plots
├── screenshots/                    # dashboard screenshots for README/portfolio
├── requirements.txt
└── README.md
```

---

## 8. Build Timeline

| Week | Milestone |
|---|---|
| Week 1 | Data generation/sourcing, cleaning, derive revenue/profit/margin fields, plant underperforming segment |
| Week 2 | SQL: build star schema DDL, load data, write & validate analysis queries |
| Week 3 | Power BI: import model, wire relationships, mark date table, write & test all DAX measures |
| Week 4 | Build report pages, styling, recommendations page, README + screenshots |

---

## 9. Interview-Defensibility Checklist

1. **Why a star schema instead of one flat table?** → Explain normalization, DAX time-intelligence requiring a proper Date dimension, performance at scale.
2. **What makes `Dim_Date` special — why "mark as date table"?** → It must be continuous (no gaps) and marked so `SAMEPERIODLASTYEAR`/`DATESINPERIOD` resolve correctly; otherwise these functions silently give wrong results.
3. **How did you validate your DAX measures were correct?** → Cross-checked against raw SQL aggregation queries (Stage 3) — same numbers, two methods.
4. **How did you actually identify the underperforming segment — what was the finding?** → Be ready with the real number from your `Underperformer Flag` output (margin %, return rate) and the specific region/category combination.
5. **What's the difference between `CALCULATE` + `DATESINPERIOD` vs just filtering the visual to last 30 days?** → `DATESINPERIOD` inside a measure recalculates correctly regardless of what date range the user has selected/filtered elsewhere on the report — it's a proper rolling window, not a static filter.
6. **What would you do differently with 10x the data?** → Move Power BI to DirectQuery/Import with incremental refresh, consider a proper data warehouse (e.g., Snowflake, matches your existing cert) instead of local PostgreSQL.

---

## 10. Optional Stretch Goals
- Add a **What-If parameter** in Power BI (e.g., "discount sensitivity slider") to simulate margin impact — shows advanced DAX skills.
- Publish to Power BI Service and add a scheduled refresh story (even against a static file) to talk about "production" deployment.
- Add a `Dim_Supplier` table and supply-chain-specific metrics like **days of inventory on hand** or **reorder point** if you want the "supply chain" half of the title to have deeper substance beyond just returns/margin.
- Use **Snowflake** (you're already certified) instead of PostgreSQL as the backing database, to tie this project to your other certifications.

---

### Next steps
Feed Stages 1–3 into Antigravity as separate prompts (Python ETL → SQL DDL/load → SQL analysis queries). Once those outputs exist, move into Power BI Desktop yourself for Stages 4–6, using `dax/measures.dax` as your paste-in reference. Keep this file as the source-of-truth spec across sessions.
