# Enterprise Retail Sales & Supply Chain Analytics

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white"/>
  <img src="https://img.shields.io/badge/Power_BI-F2C811?style=for-the-badge&logo=powerbi&logoColor=black"/>
  <img src="https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white"/>
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white"/>
  <img src="https://img.shields.io/badge/GitHub_Actions-2088FF?style=for-the-badge&logo=github-actions&logoColor=white"/>
</p>

<p align="center">
  An end-to-end enterprise analytics portfolio project demonstrating a full data engineering + analytics lifecycle — from raw CSV to star-schema SQL database to dual-dashboard deployment (Power BI + Streamlit).
</p>

---

## 🔗 Live Demo

| Platform | Link |
|---|---|
| 🌐 **Streamlit Dashboard** | _Deploy via Streamlit Cloud — see [Deployment](#deployment) section_ |
| 📊 **Power BI Report** | `powerbi/retail_dashboard.pbix` (see [Power BI Instructions](POWER_BI_INSTRUCTIONS.md)) |
| 💻 **GitHub Repo** | https://github.com/Aakash-Kumawat-621/Enterprise-Sales-Supply-Dashboard |

---

## 📖 Project Overview

This project models a **real enterprise analytics workflow** for a global retail business:

1. **Raw Data**: Kaggle Superstore dataset (`data/raw/`) — ~9,994 order lines across 4 years.
2. **ETL Pipeline** (`src/`): Cleans, reshapes into a star schema, augments to 100K rows, and loads into SQLite.
3. **SQL Analysis** (`sql/`): Four production-grade queries with window functions surface KPIs and identify underperformers.
4. **DAX Measures** (`dax/`): Eight Power BI measures cross-validate the SQL findings.
5. **Dual Dashboards**: A Power BI `.pbix` for offline use and a Streamlit web app for public portfolio deployment.

### Key Finding (The "Planted Anomaly")

> **Furniture → Tables in the South Region** was identified as the critical underperformer:
> - Margin: **−12.1%** vs. a positive global average
> - Return Rate: **21.3%** (5× the 4% dataset baseline)
> - Avg Discount: **50.1%** (causing direct margin destruction)
> - Net Profit Impact: **−$11,165**

This anomaly was injected via the augmentation pipeline (`src/augment_data.py`) to demonstrate the ability to model synthetic bias, then independently detect it via SQL, DAX, and Python.

---

## 🏗️ Architecture

```
Raw CSV
  │
  ▼
src/clean_transform.py   ← Phase 3: ETL → 5 star-schema CSVs
  │
  ▼
src/augment_data.py      ← Phase 4: Scale to 100K rows, inject bias
  │
  ▼
src/load_to_db.py        ← Phase 5a: Load into SQLite (retail_analytics.db)
  │
  ▼
sql/analysis_queries.sql ← Phase 5b: 4 SQL queries (window functions, CTEs)
  │
  ├──► dax/measures.dax  ← Phase 6: 8 DAX measures for Power BI
  │
  └──► app.py            ← Phase 7.5: Streamlit dashboard (public deployment)
```

### Star Schema

```
              ┌─────────────┐
              │  Dim_Date   │
              │  (1,461 rows│
              │  continuous)│
              └──────┬──────┘
                     │ date_id
     ┌───────────────┼───────────────┐
     │               │               │
┌────┴─────┐   ┌─────┴──────┐  ┌────┴──────┐
│Dim_Region│   │ Fact_Sales  │  │Dim_Customer│
│(13 rows) │───│(100,000 rows│──│(795 rows)  │
└──────────┘   │ granularity:│  └────────────┘
               │ order line) │
               └─────┬───────┘
                     │
               ┌─────┴──────┐
               │ Dim_Product │
               │(10,051 rows)│
               │ 3 categories│
               │17 sub-cats  │
               └────────────┘
```

---

## 📁 Repository Structure

```
.
├── app.py                        # Streamlit web dashboard (Phase 7.5)
├── POWER_BI_INSTRUCTIONS.md      # Step-by-step Power BI build guide (Phase 7)
├── METHODOLOGY.md                # Design decisions & synthetic data justifications
├── requirements.txt              # Pinned Python dependencies
├── Makefile                      # make etl | make app | make docker-run
├── Dockerfile                    # Container for Streamlit dashboard
├── docker-compose.yml            # Orchestrates etl + dashboard services
│
├── data/
│   ├── raw/                      # Original Superstore CSV (gitignored)
│   └── processed/                # Star-schema CSVs (gitignored)
│
├── src/
│   ├── clean_transform.py        # Phase 3 ETL — raw → star schema
│   ├── augment_data.py           # Phase 4 — scale to 100K rows, inject bias
│   ├── load_to_db.py             # Phase 5a — load CSVs → SQLite
│   └── run_analysis_queries.py   # Phase 5b — execute SQL, save results
│
├── sql/
│   ├── ddl_create_star_schema.sql # Full SQLite DDL with FKs and indexes
│   └── analysis_queries.sql       # 4 analysis queries (window functions, CTEs)
│
├── dax/
│   └── measures.dax              # 8 Power BI DAX measures
│
├── notebooks/                    # EDA notebooks (planned)
├── powerbi/                      # .pbix file (gitignored)
├── screenshots/                  # Dashboard screenshots for README
└── .github/workflows/etl.yml     # GitHub Actions CI pipeline
```

---

## ⚙️ Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Language | Python 3.11+ | |
| ETL | Pandas, NumPy | Star schema reshaping, synthetic field generation |
| Database | SQLite (via SQLAlchemy) | Zero-config, portable; DDL is PostgreSQL-compatible |
| SQL | SQLite 3.25+ | Window functions (`LAG`, `SUM OVER`), CTEs |
| BI (offline) | Power BI Desktop | 4-page report, 8 DAX measures, time-intelligence |
| Web Dashboard | Streamlit + Plotly | Dark mode, glassmorphism UI, interactive filters |
| Containerisation | Docker + Compose | `etl` and `dashboard` services |
| CI/CD | GitHub Actions | Runs ETL on every push to `src/` or `sql/` |
| Dependency Mgmt | pip + `requirements.txt` | Pinned versions for reproducibility |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- The Kaggle Superstore CSV placed at `data/raw/SuperStore_Orders.csv`

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Full ETL Pipeline
```bash
# Option A — Make (recommended)
make etl

# Option B — Manual
python src/clean_transform.py
python src/augment_data.py
python src/load_to_db.py
```

### 3. Run SQL Analysis Queries
```bash
python src/run_analysis_queries.py
```

### 4. Launch the Streamlit Dashboard
```bash
streamlit run app.py
# Opens at http://localhost:8501
```

### 5. Docker (alternative)
```bash
make docker-run
# Streamlit served at http://localhost:8501
```

---

## 📊 ETL Pipeline Details

### Phase 3 — `src/clean_transform.py`
Transforms the raw Superstore CSV into 5 star-schema tables:

| Table | Rows | Notes |
|---|---|---|
| `Dim_Date` | 1,461 | **Continuous** calendar (no gaps) — required for Power BI time-intelligence |
| `Dim_Product` | 10,051 | Includes both `category` (3) and `sub_category` (17) for drill-down |
| `Dim_Region` | 13 | Global regions across 7 markets |
| `Dim_Customer` | 795 | Consumer / Corporate / Home Office segments |
| `Fact_Sales` | 100,000 | After Phase 4 augmentation |

**Synthetic Fields** (see [METHODOLOGY.md](METHODOLOGY.md) for full justification):
- `returned_flag` — ~4% True rate (pseudorandom, seeded)
- `supplier` — deterministic mapping per sub-category
- `signup_date` — approximated from each customer's earliest order date

### Phase 4 — `src/augment_data.py`
Scales the dataset to enterprise proportions and injects a realistic underperforming segment:

```
Original rows  :  48,629
Augmented rows :  51,371  (resampled with date/quantity/discount jitter)
Final rows     : 100,000

Injected Segment (Furniture › Tables › South):
  discount_pct  :  40–60%  (mean 50.1%)
  margin_pct    : -20% to -5%  (mean -12.1%)
  returned_flag :  25% rate  (vs 4% baseline)
  total profit  : -$11,165.24
```

---

## 📈 SQL Analysis Queries

Four queries in `sql/analysis_queries.sql` using advanced SQL:

| Query | Technique | Purpose |
|---|---|---|
| Q1: Revenue by Region × Category | `GROUP BY`, `CASE` | High-level rollup, validates joins |
| Q2: Month-over-Month Trend | `LAG()`, `SUM() OVER()` | Revenue trend + YTD cumulative |
| Q3: Underperformer Detection | `CASE` flagging, `NULLIF` | Surfaces Furniture › Tables › South |
| Q4: Top/Bottom 10 Products | `ROW_NUMBER()`, CTEs | Product-level margin ranking |

---

## 📐 DAX Measures (`dax/measures.dax`)

Eight measures for Power BI — paste into any `Fact_Sales` measure group:

| Measure | DAX Functions Used |
|---|---|
| `Total Revenue` | `SUM()` |
| `Total Profit` | `SUM()` |
| `Margin %` | `DIVIDE()` |
| `Rolling 30-Day Revenue` | `CALCULATE()`, `DATESINPERIOD()` |
| `Rolling 90-Day Revenue` | `CALCULATE()`, `DATESINPERIOD()` |
| `Revenue YoY` | `SAMEPERIODLASTYEAR()`, `DIVIDE()` |
| `Return Rate` | `CALCULATE()`, `COUNTROWS()` |
| `Underperformer Flag` | `IF()`, dual-condition logic |

---

## 🌐 Deployment

### Streamlit Cloud (Recommended — Free)

1. Push this repository to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. Click **New app** → select this repo → set main file to `app.py`.
4. The `retail_analytics.db` file must be committed to the repo (it is excluded by `.gitignore` by default — remove the exception for the `.db` file if you want to deploy with live data, or generate it via the CI pipeline).

> **Note:** For a production deployment, replace SQLite with a hosted PostgreSQL instance (e.g., [Supabase free tier](https://supabase.com)) and update the `DB_URL` in `src/load_to_db.py`. The DDL and all queries are standard SQL — no other changes needed.

### Docker
```bash
docker-compose up dashboard
```

---

## 🔄 CI/CD

GitHub Actions workflow (`.github/workflows/etl.yml`) runs automatically on every push to `src/` or `sql/`:

1. Installs Python dependencies
2. Runs `clean_transform.py`
3. Runs `augment_data.py`
4. Runs `load_to_db.py`
5. Runs `run_analysis_queries.py`
6. Verifies row counts match expected values

---

## 🎯 Interview Talking Points

**"Walk me through your data model."**
> "I designed a Kimball-style star schema with a central Fact_Sales table linked to four dimension tables. The date dimension is deliberately continuous — no gaps — because Power BI's DAX time-intelligence functions like DATESINPERIOD and SAMEPERIODLASTYEAR require it. I used integer surrogate keys for all FK relationships for join performance."

**"How did you validate your Power BI numbers?"**
> "I cross-validated every KPI using three independent methods: raw SQL aggregations, DAX measures, and the Streamlit Python dashboard. All three returned identical totals. That's a strong signal the star schema relationships and measure logic are correct."

**"What did you find in the data?"**
> "Furniture → Tables in the South region showed a −12.1% margin, a 21.3% return rate which is 5× the dataset baseline, and an average discount of 50% — the clear worst-performing segment. I surfaced this first via a SQL query with a dual-condition flag, then confirmed it via the DAX Underperformer Flag measure and visualised it in the Streamlit scatter plot."

**"Why SQLite and not PostgreSQL?"**
> "For local development and portfolio portability, SQLite is ideal — zero server setup, single file, easily committed to a repo. The DDL is written in standard SQL, so switching to PostgreSQL requires only changing the SQLAlchemy connection string. I documented this decision in METHODOLOGY.md."

---

## 📝 Methodology

See [METHODOLOGY.md](METHODOLOGY.md) for detailed documentation of every design decision, including:
- Star schema design choices
- Synthetic field generation rationale
- Augmentation methodology and bias injection parameters
- Phase 4 actual run statistics

---

## 👤 Author

**Aakash Kumawat**  
[GitHub](https://github.com/Aakash-Kumawat-621) · [LinkedIn](https://linkedin.com)

---

## 📄 License

This project uses the [Kaggle Superstore dataset](https://www.kaggle.com/datasets/vivek468/superstore-dataset-final) for educational/portfolio purposes.
