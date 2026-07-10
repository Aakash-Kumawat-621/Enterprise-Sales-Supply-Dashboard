-- =============================================================================
-- ddl_create_star_schema.sql
-- Enterprise Retail Sales & Supply Chain Analytics
-- =============================================================================
-- Database  : SQLite
-- Note      : SQLite is chosen over PostgreSQL for local simplicity —
--             zero server setup, single portable file. The DDL uses standard
--             SQL; switching to PostgreSQL requires only changing the
--             SQLAlchemy connection string in load_to_db.py, not these queries.
-- FK note   : SQLite supports FK constraints but disables them by default.
--             Run `PRAGMA foreign_keys = ON;` at the start of every session.
-- =============================================================================

PRAGMA foreign_keys = ON;

-- -----------------------------------------------------------------------------
-- Drop tables in reverse dependency order (FK-safe)
-- -----------------------------------------------------------------------------
DROP TABLE IF EXISTS Fact_Sales;
DROP TABLE IF EXISTS Dim_Date;
DROP TABLE IF EXISTS Dim_Product;
DROP TABLE IF EXISTS Dim_Region;
DROP TABLE IF EXISTS Dim_Customer;

-- -----------------------------------------------------------------------------
-- Dim_Date
-- Grain: one row per calendar day, continuous with no gaps.
-- This is a hard requirement for Power BI's "Mark as Date Table" and for
-- DAX time-intelligence functions (DATESINPERIOD, SAMEPERIODLASTYEAR).
-- date_id format: YYYYMMDD integer — fast joins, human-readable.
-- -----------------------------------------------------------------------------
CREATE TABLE Dim_Date (
    date_id      INTEGER PRIMARY KEY,   -- YYYYMMDD, e.g. 20130715
    full_date    TEXT    NOT NULL,       -- ISO 8601: 'YYYY-MM-DD'
    year         INTEGER NOT NULL,
    quarter      INTEGER NOT NULL CHECK (quarter BETWEEN 1 AND 4),
    month        INTEGER NOT NULL CHECK (month   BETWEEN 1 AND 12),
    month_name   TEXT    NOT NULL,
    week_of_year INTEGER NOT NULL,
    day_of_week  INTEGER NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),  -- Mon=0
    day_name     TEXT    NOT NULL,
    is_weekend   INTEGER NOT NULL CHECK (is_weekend IN (0, 1)),          -- boolean
    fiscal_year  INTEGER NOT NULL       -- Apr–Mar fiscal calendar
);

-- -----------------------------------------------------------------------------
-- Dim_Product
-- Grain: one row per unique product (identified by source_product_id).
-- product_key is a numeric surrogate PK (source_product_id kept for traceability).
-- Includes BOTH category (3 values) and sub_category (17 values) to represent
-- the hierarchical product taxonomy — required for category→sub-category drill-down.
-- -----------------------------------------------------------------------------
CREATE TABLE Dim_Product (
    product_key      INTEGER PRIMARY KEY,
    source_product_id TEXT   NOT NULL,     -- original Kaggle product ID string
    product_name     TEXT    NOT NULL,
    category         TEXT    NOT NULL,     -- 3 categories: Furniture, Office Supplies, Technology
    sub_category     TEXT    NOT NULL,     -- 17 sub-categories
    unit_cost        REAL,                 -- mean unit cost across all transactions
    supplier         TEXT                  -- SYNTHETIC — see METHODOLOGY.md §3.2
);

-- -----------------------------------------------------------------------------
-- Dim_Region
-- Grain: one row per named region (13 global regions, 7 markets).
-- Note: country omitted — it is many-to-one with region and does not fit a
-- single dimension row (many countries per region in this global dataset).
-- -----------------------------------------------------------------------------
CREATE TABLE Dim_Region (
    region_id    INTEGER PRIMARY KEY,
    region_name  TEXT    NOT NULL,
    market       TEXT    NOT NULL,   -- parent grouping: Africa, APAC, EMEA, EU, Canada, LATAM, US
    warehouse_id TEXT    NOT NULL    -- SYNTHETIC — one warehouse per region
);

-- -----------------------------------------------------------------------------
-- Dim_Customer
-- Grain: one row per unique customer × segment combination.
-- customer_id: numeric surrogate (no natural key in source data).
-- signup_date: APPROXIMATED as earliest order_date — see METHODOLOGY.md §3.3.
-- -----------------------------------------------------------------------------
CREATE TABLE Dim_Customer (
    customer_id      INTEGER PRIMARY KEY,
    customer_name    TEXT    NOT NULL,
    customer_segment TEXT    NOT NULL,  -- Consumer, Corporate, Home Office
    signup_date      TEXT                -- ISO 8601 date string
);

-- -----------------------------------------------------------------------------
-- Fact_Sales
-- Grain: one row per order line item (order_id × product).
-- sales_id: sequential surrogate PK.
-- All FK columns reference dimension surrogate keys.
-- returned_flag: SYNTHETIC (~4% baseline, 25% in underperforming segment).
-- -----------------------------------------------------------------------------
CREATE TABLE Fact_Sales (
    sales_id       INTEGER PRIMARY KEY,
    order_id       TEXT    NOT NULL,
    date_id        INTEGER NOT NULL REFERENCES Dim_Date(date_id),
    product_id     INTEGER NOT NULL REFERENCES Dim_Product(product_key),
    region_id      INTEGER NOT NULL REFERENCES Dim_Region(region_id),
    customer_id    INTEGER NOT NULL REFERENCES Dim_Customer(customer_id),
    quantity       INTEGER NOT NULL CHECK (quantity >= 1),
    unit_price     REAL    NOT NULL,
    discount_pct   REAL    NOT NULL CHECK (discount_pct BETWEEN 0.0 AND 1.0),
    gross_revenue  REAL    NOT NULL,
    net_revenue    REAL    NOT NULL,
    cost           REAL    NOT NULL,
    profit         REAL    NOT NULL,
    margin_pct     REAL    NOT NULL,
    returned_flag  INTEGER NOT NULL CHECK (returned_flag IN (0, 1)),  -- boolean
    shipping_cost  REAL,
    ship_mode      TEXT,
    order_priority TEXT
);

-- -----------------------------------------------------------------------------
-- Indexes — improve query performance for common join + filter patterns
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_fact_date     ON Fact_Sales(date_id);
CREATE INDEX IF NOT EXISTS idx_fact_product  ON Fact_Sales(product_id);
CREATE INDEX IF NOT EXISTS idx_fact_region   ON Fact_Sales(region_id);
CREATE INDEX IF NOT EXISTS idx_fact_customer ON Fact_Sales(customer_id);
CREATE INDEX IF NOT EXISTS idx_dim_date_year ON Dim_Date(year, month);
CREATE INDEX IF NOT EXISTS idx_prod_category ON Dim_Product(category, sub_category);
