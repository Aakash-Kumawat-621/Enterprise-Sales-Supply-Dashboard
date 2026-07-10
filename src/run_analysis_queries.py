"""
run_analysis_queries.py
=======================
ETL — Phase 5b: Execute the four SQL analysis queries from
sql/analysis_queries.sql against the SQLite database.

Outputs:
    - Prints the underperformer query result to console (for visual confirmation)
    - Saves all four query results to data/processed/sql_validation_results.csv
      (multi-sheet via sheet name embedded in a "query" column)

Interview talking point:
    "I cross-validated my Power BI DAX measures against these raw SQL
     aggregation results — same total revenue, same underperformer,
     two independent computation paths."
"""

import sys
import re
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# ── Configuration ─────────────────────────────────────────────────────────────
DB_PATH     = Path("retail_analytics.db")
DB_URL      = f"sqlite:///{DB_PATH}"
SQL_FILE    = Path("sql/analysis_queries.sql")
OUTPUT_DIR  = Path("data/processed")
OUTPUT_FILE = OUTPUT_DIR / "sql_validation_results.csv"

print("=" * 65)
print("PHASE 5b — Run SQL Analysis Queries")
print("=" * 65)

# ─────────────────────────────────────────────────────────────────────────────
# Parse the SQL file — split on QUERY header comments
# Each query block starts with: -- QUERY N:
# ─────────────────────────────────────────────────────────────────────────────
sql_text = SQL_FILE.read_text(encoding="utf-8")

# Split on the decorated query-header comment blocks
query_blocks = re.split(r"-{79,}\n-- QUERY \d+:", sql_text)

# Parse query names and bodies
QUERIES = {
    "Q1_Revenue_by_Region_Category"     : None,
    "Q2_Month_over_Month_Trend"         : None,
    "Q3_Underperformer_Detection"       : None,
    "Q4_Top_Bottom_Products_by_Margin"  : None,
}

# Alternative: define queries inline (more robust than regex parsing)
# These are identical to sql/analysis_queries.sql — kept in sync manually.
engine = create_engine(DB_URL)

QUERY_DEFS = {
    "Q1_Revenue_by_Region_Category": """
        SELECT
            r.region_name,
            r.market,
            p.category,
            COUNT(*)                        AS order_lines,
            SUM(f.quantity)                 AS total_units,
            ROUND(SUM(f.net_revenue), 2)    AS total_revenue,
            ROUND(SUM(f.profit), 2)         AS total_profit,
            ROUND(
                SUM(f.profit) * 100.0 / NULLIF(SUM(f.net_revenue), 0),
                2
            )                               AS margin_pct,
            ROUND(
                SUM(CASE WHEN f.returned_flag = 1 THEN 1.0 ELSE 0.0 END)
                / COUNT(*) * 100.0,
                2
            )                               AS return_rate_pct
        FROM Fact_Sales      f
        JOIN Dim_Region   r ON f.region_id  = r.region_id
        JOIN Dim_Product  p ON f.product_id = p.product_key
        GROUP BY
            r.region_name, r.market, p.category
        ORDER BY
            total_revenue DESC
    """,

    "Q2_Month_over_Month_Trend": """
        WITH monthly_revenue AS (
            SELECT
                d.year,
                d.month,
                d.month_name,
                ROUND(SUM(f.net_revenue), 2)  AS monthly_revenue,
                ROUND(SUM(f.profit), 2)       AS monthly_profit
            FROM Fact_Sales   f
            JOIN Dim_Date  d ON f.date_id = d.date_id
            GROUP BY
                d.year, d.month, d.month_name
        )
        SELECT
            year,
            month,
            month_name,
            monthly_revenue,
            monthly_profit,
            ROUND(
                monthly_revenue
                - LAG(monthly_revenue, 1, 0) OVER (ORDER BY year, month),
                2
            )                                        AS mom_revenue_change,
            ROUND(
                (monthly_revenue - LAG(monthly_revenue, 1) OVER (ORDER BY year, month))
                * 100.0
                / NULLIF(LAG(monthly_revenue, 1) OVER (ORDER BY year, month), 0),
                2
            )                                        AS mom_revenue_pct,
            ROUND(
                SUM(monthly_revenue) OVER (
                    PARTITION BY year
                    ORDER BY year, month
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ),
                2
            )                                        AS ytd_revenue
        FROM monthly_revenue
        ORDER BY
            year, month
    """,

    "Q3_Underperformer_Detection": """
        SELECT
            r.region_name,
            r.market,
            p.category,
            p.sub_category,
            COUNT(*)                                                    AS order_lines,
            ROUND(SUM(f.net_revenue), 2)                                AS total_revenue,
            ROUND(SUM(f.profit), 2)                                     AS total_profit,
            ROUND(
                SUM(f.profit) * 100.0 / NULLIF(SUM(f.net_revenue), 0),
                2
            )                                                           AS margin_pct,
            ROUND(AVG(f.discount_pct) * 100.0, 2)                      AS avg_discount_pct,
            ROUND(
                SUM(CASE WHEN f.returned_flag = 1 THEN 1.0 ELSE 0.0 END)
                / COUNT(*) * 100.0,
                2
            )                                                           AS return_rate_pct,
            CASE
                WHEN SUM(f.profit) * 1.0 / NULLIF(SUM(f.net_revenue), 0) < 0.05
                 AND SUM(CASE WHEN f.returned_flag = 1 THEN 1.0 ELSE 0.0 END)
                     / COUNT(*) > 0.15
                THEN 'Underperforming'
                ELSE 'Healthy'
            END                                                         AS performance_flag
        FROM Fact_Sales      f
        JOIN Dim_Region   r ON f.region_id  = r.region_id
        JOIN Dim_Product  p ON f.product_id = p.product_key
        GROUP BY
            r.region_name, r.market, p.category, p.sub_category
        ORDER BY
            margin_pct ASC,
            return_rate_pct DESC
    """,

    "Q4_Top_Bottom_Products_by_Margin": """
        WITH product_margins AS (
            SELECT
                p.product_key,
                p.source_product_id,
                p.product_name,
                p.category,
                p.sub_category,
                p.supplier,
                COUNT(*)                                                AS order_lines,
                SUM(f.quantity)                                         AS total_units,
                ROUND(SUM(f.net_revenue), 2)                            AS total_revenue,
                ROUND(SUM(f.profit), 2)                                 AS total_profit,
                ROUND(
                    SUM(f.profit) * 100.0 / NULLIF(SUM(f.net_revenue), 0),
                    2
                )                                                       AS margin_pct,
                ROUND(
                    SUM(CASE WHEN f.returned_flag = 1 THEN 1.0 ELSE 0.0 END)
                    / COUNT(*) * 100.0,
                    2
                )                                                       AS return_rate_pct
            FROM Fact_Sales      f
            JOIN Dim_Product  p ON f.product_id = p.product_key
            GROUP BY
                p.product_key, p.source_product_id, p.product_name,
                p.category, p.sub_category, p.supplier
            HAVING COUNT(*) >= 5
        ),
        ranked AS (
            SELECT
                *,
                ROW_NUMBER() OVER (ORDER BY margin_pct DESC) AS rank_top,
                ROW_NUMBER() OVER (ORDER BY margin_pct ASC)  AS rank_bottom
            FROM product_margins
        )
        SELECT
            CASE
                WHEN rank_top    <= 10 THEN 'Top 10'
                WHEN rank_bottom <= 10 THEN 'Bottom 10'
            END        AS tier,
            rank_top,
            rank_bottom,
            product_name,
            category,
            sub_category,
            supplier,
            order_lines,
            total_units,
            total_revenue,
            total_profit,
            margin_pct,
            return_rate_pct
        FROM ranked
        WHERE rank_top <= 10 OR rank_bottom <= 10
        ORDER BY
            margin_pct DESC
    """,
}

# ─────────────────────────────────────────────────────────────────────────────
# Execute queries and collect results
# ─────────────────────────────────────────────────────────────────────────────
print(f"\nConnecting to: {DB_PATH}")
all_results = []

with engine.connect() as conn:
    conn.execute(text("PRAGMA foreign_keys = ON"))

    for qname, qsql in QUERY_DEFS.items():
        print(f"\n{'─'*65}")
        print(f"  Running {qname} ...")
        df = pd.read_sql(text(qsql), conn)
        df.insert(0, "query", qname)   # tag rows with query name for the combined CSV
        all_results.append(df)
        print(f"  Returned {len(df):,} rows")

        # ── Print Q3 (underperformer) in full so user can visually confirm ──
        if qname == "Q3_Underperformer_Detection":
            print()
            print("  *** UNDERPERFORMER DETECTION RESULTS ***")
            print("  (Confirm Furniture > Tables > South is at the top)")
            print()
            pd.set_option("display.max_columns", None)
            pd.set_option("display.width", 140)
            pd.set_option("display.float_format", "{:.2f}".format)
            top20 = df.drop(columns=["query"]).head(20)
            print(top20.to_string(index=False))
            print()
            # Highlight the planted underperformer explicitly
            hit = df[
                (df["category"] == "Furniture") &
                (df["sub_category"] == "Tables") &
                (df["region_name"] == "South")
            ]
            if not hit.empty:
                row = hit.iloc[0]
                print("  ✅  PLANTED SEGMENT CONFIRMED:")
                print(f"      Region       : {row['region_name']}")
                print(f"      Category     : {row['category']}")
                print(f"      Sub-Category : {row['sub_category']}")
                print(f"      Margin %     : {row['margin_pct']:.2f}%")
                print(f"      Return Rate  : {row['return_rate_pct']:.2f}%")
                print(f"      Avg Discount : {row['avg_discount_pct']:.2f}%")
                print(f"      Total Profit : ${row['total_profit']:,.2f}")
                print(f"      Flag         : {row['performance_flag']}")
            else:
                print("  ⚠️  WARNING: Planted segment NOT found in results — "
                      "check augmentation step.")

# ─────────────────────────────────────────────────────────────────────────────
# Save all results to a single combined CSV
# ─────────────────────────────────────────────────────────────────────────────
combined = pd.concat(all_results, ignore_index=True)
combined.to_csv(OUTPUT_FILE, index=False)

print(f"\n{'='*65}")
print(f"✅  All queries complete.")
print(f"    Results saved to: {OUTPUT_FILE}")
print(f"    Total rows across all queries: {len(combined):,}")
print()
print("  ➜  Next: run src/generate_dax.py  OR  open dax/measures.dax")
print("          and paste measures into Power BI Desktop.")
