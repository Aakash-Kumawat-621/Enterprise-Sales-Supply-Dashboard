-- =============================================================================
-- analysis_queries.sql
-- Enterprise Retail Sales & Supply Chain Analytics — Phase 5, Stage 3
-- =============================================================================
-- Four SQL analysis queries that:
--   1. Validate the star schema is loaded correctly.
--   2. Cross-validate the DAX measures in dax/measures.dax against raw SQL.
--   3. Surface the planted underperforming segment (Furniture > Tables, South).
--
-- All queries are standard SQL (SQLite 3.25+ window function syntax).
-- Run via: python src/run_analysis_queries.py
-- Results saved to: data/processed/sql_validation_results.csv
--
-- Interview talking point:
--   "I cross-validated my Power BI DAX measures against these raw SQL
--    aggregations to confirm the numbers matched — same revenue totals,
--    same underperformer, two independent computation paths."
-- =============================================================================

PRAGMA foreign_keys = ON;


-- =============================================================================
-- QUERY 1: Revenue by Region and Category
-- Purpose : High-level rollup — confirms star schema joins work and gives
--           the region × category breakdown shown on Power BI Page 2.
-- =============================================================================

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
    total_revenue DESC;


-- =============================================================================
-- QUERY 2: Month-over-Month Revenue Trend (Window Functions)
-- Purpose : Validates rolling/trend logic that DAX Rolling 30/90-day and
--           YoY measures reproduce. Uses LAG() and cumulative SUM() OVER().
-- =============================================================================

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
    -- Month-over-month change (absolute)
    ROUND(
        monthly_revenue
        - LAG(monthly_revenue, 1, 0) OVER (ORDER BY year, month),
        2
    )                                                    AS mom_revenue_change,
    -- Month-over-month % change
    ROUND(
        (monthly_revenue - LAG(monthly_revenue, 1) OVER (ORDER BY year, month))
        * 100.0
        / NULLIF(LAG(monthly_revenue, 1) OVER (ORDER BY year, month), 0),
        2
    )                                                    AS mom_revenue_pct,
    -- Cumulative revenue (running total)
    ROUND(
        SUM(monthly_revenue) OVER (
            PARTITION BY year
            ORDER BY year, month
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ),
        2
    )                                                    AS ytd_revenue
FROM monthly_revenue
ORDER BY
    year, month;


-- =============================================================================
-- QUERY 3: Return Rate and Margin % by Category × Region (Underperformer Detection)
-- Purpose : MUST surface Furniture > Tables > South as the clear worst
--           performer. Cross-validates the DAX Underperformer Flag measure.
--           "I identified the underperforming segment via raw SQL before
--            confirming the same finding in Power BI."
-- =============================================================================

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
    -- Performance flag (mirrors DAX Underperformer Flag logic)
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
    margin_pct ASC,        -- worst margin at top
    return_rate_pct DESC;  -- break ties by highest return rate


-- =============================================================================
-- QUERY 4: Top 10 and Bottom 10 Products by Profit Margin
-- Purpose : Product-level deep dive for Power BI Page 3 (Inventory Health).
--           Surfaces which specific products are drag vs. lift on margins.
-- =============================================================================

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
    HAVING COUNT(*) >= 5   -- minimum transaction threshold for stable margin estimate
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
    margin_pct DESC;
