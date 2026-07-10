"""
app.py — Enterprise Retail Sales & Supply Chain Analytics Dashboard
====================================================================
Streamlit + Plotly web dashboard for public portfolio deployment.
Mirrors all 4 Power BI pages with full interactivity.

Run locally:
    streamlit run app.py

Deploy on Streamlit Cloud:
    Push this repo to GitHub and connect it at share.streamlit.io
    Set the main file path to: app.py
"""

import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Enterprise Retail Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com/Aakash-Kumawat-621/Enterprise-Sales-Supply-Dashboard",
        "About": "Enterprise Retail Sales & Supply Chain Analytics — built with Python, SQLite, Plotly & Streamlit.",
    },
)

# ─── Global CSS: Dark Mode + Glassmorphism ────────────────────────────────────
st.markdown(
    """
    <style>
    /* ── Import Fonts ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* ── Global Dark Background ── */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
        background: linear-gradient(135deg, #0a0f1e 0%, #0d1b35 50%, #0a0f1e 100%) !important;
        font-family: 'Inter', sans-serif !important;
        color: #e2e8f0 !important;
    }
    [data-testid="stSidebar"] {
        background: rgba(255, 255, 255, 0.04) !important;
        backdrop-filter: blur(20px);
        border-right: 1px solid rgba(255,255,255,0.08);
    }
    [data-testid="stHeader"] { background: transparent !important; }
    .block-container { padding: 1.5rem 2.5rem 2rem 2.5rem; }

    /* ── Glassmorphism KPI Cards ── */
    .kpi-card {
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 16px;
        padding: 24px 28px;
        backdrop-filter: blur(12px);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    .kpi-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
        border-radius: 16px 16px 0 0;
    }
    .kpi-card.revenue::before { background: linear-gradient(90deg, #3b82f6, #06b6d4); }
    .kpi-card.profit::before  { background: linear-gradient(90deg, #10b981, #34d399); }
    .kpi-card.margin::before  { background: linear-gradient(90deg, #8b5cf6, #a78bfa); }
    .kpi-card.returns::before { background: linear-gradient(90deg, #f59e0b, #fcd34d); }
    .kpi-card:hover {
        background: rgba(255, 255, 255, 0.1);
        border-color: rgba(255, 255, 255, 0.2);
        transform: translateY(-2px);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.3);
    }
    .kpi-label {
        font-size: 11px; font-weight: 600;
        text-transform: uppercase; letter-spacing: 1.5px;
        color: #94a3b8; margin-bottom: 8px;
    }
    .kpi-value {
        font-size: 32px; font-weight: 700;
        color: #f1f5f9; line-height: 1.1;
    }
    .kpi-delta {
        font-size: 12px; margin-top: 6px; color: #94a3b8;
    }
    .kpi-delta.positive { color: #34d399; }
    .kpi-delta.negative { color: #f87171; }

    /* ── Section Headers ── */
    .section-header {
        font-size: 22px; font-weight: 700; color: #f1f5f9;
        border-left: 4px solid #3b82f6; padding-left: 14px;
        margin: 28px 0 18px 0;
    }

    /* ── Alert Banner ── */
    .alert-banner {
        background: linear-gradient(135deg, rgba(239,68,68,0.15), rgba(220,38,38,0.08));
        border: 1px solid rgba(239,68,68,0.4);
        border-left: 4px solid #ef4444;
        border-radius: 12px;
        padding: 18px 22px;
        margin-bottom: 20px;
        animation: pulse-border 2.5s infinite;
    }
    @keyframes pulse-border {
        0%, 100% { border-left-color: #ef4444; }
        50%       { border-left-color: #fca5a5; }
    }
    .alert-title { font-size: 16px; font-weight: 700; color: #fca5a5; margin-bottom: 6px; }
    .alert-body  { font-size: 14px; color: #fecaca; line-height: 1.6; }

    /* ── Info Cards (Recommendations) ── */
    .rec-card {
        background: rgba(59, 130, 246, 0.08);
        border: 1px solid rgba(59, 130, 246, 0.25);
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 14px;
        transition: background 0.2s;
    }
    .rec-card:hover { background: rgba(59, 130, 246, 0.14); }
    .rec-title { font-size: 15px; font-weight: 600; color: #93c5fd; margin-bottom: 6px; }
    .rec-body  { font-size: 13px; color: #cbd5e1; line-height: 1.7; }

    /* ── Sidebar polish ── */
    .sidebar-logo {
        font-size: 20px; font-weight: 800;
        background: linear-gradient(90deg, #3b82f6, #06b6d4);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 4px;
    }
    .sidebar-sub { font-size: 11px; color: #64748b; margin-bottom: 16px; }
    [data-testid="stSidebar"] label { color: #94a3b8 !important; font-size: 13px; }
    [data-testid="stSidebar"] .stRadio > div { gap: 6px; }
    [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.08); }

    /* ── Dataframe ── */
    [data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─── Constants ────────────────────────────────────────────────────────────────
DB_PATH = Path("retail_analytics.db")

PLOTLY_THEME = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(255,255,255,0.03)",
    font=dict(family="Inter", color="#94a3b8"),
    title_font=dict(family="Inter", size=15, color="#e2e8f0"),
    margin=dict(l=16, r=16, t=44, b=16),
    colorway=["#3b82f6", "#10b981", "#8b5cf6", "#f59e0b", "#ef4444",
               "#06b6d4", "#ec4899", "#84cc16"],
)

# ─── Data Loader (cached) ─────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def sql(query: str) -> pd.DataFrame:
    """Execute a SQL query against the local SQLite database."""
    if not DB_PATH.exists():
        st.error(
            f"**Database not found:** `{DB_PATH}`\n\n"
            "Run the full ETL pipeline first:\n```\npython src/clean_transform.py\n"
            "python src/augment_data.py\npython src/load_to_db.py\n```"
        )
        return pd.DataFrame()
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            return pd.read_sql(query, conn)
    except Exception as exc:
        st.error(f"Query error: {exc}")
        return pd.DataFrame()


# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-logo">📊 RetailIQ</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-sub">Enterprise Analytics Dashboard</div>', unsafe_allow_html=True)
    st.markdown("---")

    page = st.radio(
        "Navigate",
        options=["Executive Summary", "Region Deep-Dive", "Inventory Health", "Strategic Recommendations"],
        label_visibility="collapsed",
    )

    st.markdown("---")

    # Global Year Filter
    years_df = sql("SELECT DISTINCT year FROM Dim_Date ORDER BY year")
    all_years = years_df["year"].tolist() if not years_df.empty else [2011, 2012, 2013, 2014]
    selected_years = st.multiselect("Filter by Year", all_years, default=all_years)
    year_filter = f"({','.join(map(str, selected_years))})" if selected_years else "(0)"

    # Category Filter
    cats_df = sql("SELECT DISTINCT category FROM Dim_Product ORDER BY category")
    all_cats = cats_df["category"].tolist() if not cats_df.empty else []
    selected_cats = st.multiselect("Filter by Category", all_cats, default=all_cats)
    cat_filter = "(" + ",".join(f"'{c}'" for c in selected_cats) + ")" if selected_cats else "('')"

    st.markdown("---")
    st.markdown(
        """
        <div style='font-size:11px;color:#475569;line-height:1.8;'>
        <b style='color:#64748b;'>Tech Stack</b><br>
        🐍 Python · Pandas · SQLAlchemy<br>
        🗄️ SQLite Star Schema<br>
        📊 Streamlit · Plotly<br>
        🔄 GitHub Actions CI<br>
        🐳 Docker
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─── Helper: Plotly chart wrapper ────────────────────────────────────────────
def styled_chart(fig: go.Figure, height: int = 380) -> go.Figure:
    fig.update_layout(height=height, **PLOTLY_THEME)
    return fig


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — EXECUTIVE SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════
if page == "Executive Summary":
    st.markdown("## Executive Summary")
    st.markdown(
        "<p style='color:#64748b;font-size:14px;margin-top:-12px;margin-bottom:20px;'>"
        "Global performance overview · 2011–2014 · 100K order lines</p>",
        unsafe_allow_html=True,
    )

    # ── KPIs ──
    kpi = sql(f"""
        SELECT
            SUM(f.net_revenue)                                        AS revenue,
            SUM(f.profit)                                             AS profit,
            SUM(f.profit)*1.0 / NULLIF(SUM(f.net_revenue),0)         AS margin,
            SUM(CASE WHEN f.returned_flag=1 THEN 1.0 ELSE 0 END)
                / COUNT(*)                                            AS ret_rate,
            COUNT(DISTINCT f.order_id)                                AS orders,
            COUNT(DISTINCT f.customer_id)                             AS customers
        FROM Fact_Sales f
        JOIN Dim_Date d ON f.date_id = d.date_id
        WHERE d.year IN {year_filter}
    """)

    if not kpi.empty:
        r = kpi.iloc[0]
        rev, prof, marg, ret = r.revenue or 0, r.profit or 0, r.margin or 0, r.ret_rate or 0
        orders, customers = int(r.orders or 0), int(r.customers or 0)

        c1, c2, c3, c4, c5, c6 = st.columns(6)
        cards = [
            (c1, "revenue",  "Total Revenue",   f"${rev:,.0f}",            ""),
            (c2, "profit",   "Total Profit",     f"${prof:,.0f}",           ""),
            (c3, "margin",   "Margin %",         f"{marg*100:.1f}%",        ""),
            (c4, "returns",  "Return Rate",      f"{ret*100:.1f}%",         ""),
            (c5, "revenue",  "Unique Orders",    f"{orders:,}",             ""),
            (c6, "profit",   "Customers",        f"{customers:,}",          ""),
        ]
        for col, cls, label, val, delta in cards:
            with col:
                st.markdown(
                    f"""<div class="kpi-card {cls}">
                        <div class="kpi-label">{label}</div>
                        <div class="kpi-value">{val}</div>
                        <div class="kpi-delta">{delta}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )

    st.markdown('<div class="section-header">Revenue Trend</div>', unsafe_allow_html=True)

    # ── Revenue Trend ──
    trend = sql(f"""
        SELECT d.year, d.month, d.month_name,
               SUM(f.net_revenue)  AS monthly_revenue,
               SUM(f.profit)       AS monthly_profit
        FROM Fact_Sales f
        JOIN Dim_Date d ON f.date_id = d.date_id
        WHERE d.year IN {year_filter}
        GROUP BY d.year, d.month, d.month_name
        ORDER BY d.year, d.month
    """)

    if not trend.empty:
        trend["period"] = trend["year"].astype(str) + "-" + trend["month"].astype(str).str.zfill(2)
        trend["rolling_3m"] = trend["monthly_revenue"].rolling(3, min_periods=1).mean()

        fig_trend = go.Figure()
        fig_trend.add_trace(go.Bar(
            x=trend["period"], y=trend["monthly_revenue"],
            name="Monthly Revenue", marker_color="rgba(59,130,246,0.35)",
            hovertemplate="<b>%{x}</b><br>Revenue: $%{y:,.0f}<extra></extra>",
        ))
        fig_trend.add_trace(go.Scatter(
            x=trend["period"], y=trend["rolling_3m"],
            name="3-Month Rolling Avg", mode="lines",
            line=dict(color="#06b6d4", width=2.5),
            hovertemplate="<b>%{x}</b><br>Rolling Avg: $%{y:,.0f}<extra></extra>",
        ))
        fig_trend.update_layout(
            barmode="overlay", hovermode="x unified",
            xaxis=dict(tickangle=-45, nticks=20),
            yaxis_title="Revenue ($)", legend=dict(orientation="h", y=1.1),
        )
        st.plotly_chart(styled_chart(fig_trend, 380), use_container_width=True)

    # ── Revenue Split by Category ──
    st.markdown('<div class="section-header">Revenue Split</div>', unsafe_allow_html=True)
    col_l, col_r = st.columns(2)

    cat_rev = sql(f"""
        SELECT p.category, SUM(f.net_revenue) AS revenue, SUM(f.profit) AS profit
        FROM Fact_Sales f
        JOIN Dim_Product p ON f.product_id = p.product_key
        JOIN Dim_Date d ON f.date_id = d.date_id
        WHERE d.year IN {year_filter}
        GROUP BY p.category ORDER BY revenue DESC
    """)
    if not cat_rev.empty:
        with col_l:
            fig_pie = px.pie(
                cat_rev, names="category", values="revenue",
                title="Revenue by Category",
                color_discrete_sequence=["#3b82f6", "#10b981", "#8b5cf6"],
                hole=0.55,
            )
            fig_pie.update_traces(textposition="outside", textinfo="percent+label",
                                  hovertemplate="<b>%{label}</b><br>Revenue: $%{value:,.0f}<extra></extra>")
            st.plotly_chart(styled_chart(fig_pie, 360), use_container_width=True)

    yearly = sql(f"""
        SELECT d.year, p.category, SUM(f.net_revenue) AS revenue
        FROM Fact_Sales f
        JOIN Dim_Product p ON f.product_id = p.product_key
        JOIN Dim_Date d ON f.date_id = d.date_id
        WHERE d.year IN {year_filter}
        GROUP BY d.year, p.category ORDER BY d.year
    """)
    if not yearly.empty:
        with col_r:
            fig_bar = px.bar(
                yearly, x="year", y="revenue", color="category",
                title="Revenue by Year & Category", barmode="group",
                color_discrete_map={"Furniture": "#3b82f6",
                                    "Office Supplies": "#10b981",
                                    "Technology": "#8b5cf6"},
                labels={"revenue": "Revenue ($)", "year": "Year"},
            )
            fig_bar.update_traces(hovertemplate="<b>%{x}</b><br>Revenue: $%{y:,.0f}<extra></extra>")
            st.plotly_chart(styled_chart(fig_bar, 360), use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — REGION DEEP-DIVE
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "Region Deep-Dive":
    st.markdown("## Region Deep-Dive")
    st.markdown(
        "<p style='color:#64748b;font-size:14px;margin-top:-12px;margin-bottom:20px;'>"
        "Revenue, profitability and return trends broken down by region and market</p>",
        unsafe_allow_html=True,
    )

    reg = sql(f"""
        SELECT r.region_name, r.market,
               ROUND(SUM(f.net_revenue),2)   AS revenue,
               ROUND(SUM(f.profit),2)         AS profit,
               ROUND(SUM(f.profit)*100.0 / NULLIF(SUM(f.net_revenue),0),2) AS margin_pct,
               ROUND(SUM(CASE WHEN f.returned_flag=1 THEN 1.0 ELSE 0 END) / COUNT(*)*100,2) AS return_pct,
               COUNT(*)                       AS order_lines
        FROM Fact_Sales f
        JOIN Dim_Region r ON f.region_id = r.region_id
        JOIN Dim_Date d   ON f.date_id   = d.date_id
        WHERE d.year IN {year_filter}
        GROUP BY r.region_name, r.market
        ORDER BY revenue DESC
    """)

    if not reg.empty:
        col_l, col_r = st.columns(2)

        with col_l:
            st.markdown('<div class="section-header">Revenue by Region</div>', unsafe_allow_html=True)
            fig1 = px.bar(
                reg.head(13).sort_values("revenue"),
                x="revenue", y="region_name", orientation="h",
                color="margin_pct",
                color_continuous_scale="RdYlGn",
                color_continuous_midpoint=0,
                labels={"revenue": "Revenue ($)", "region_name": "Region", "margin_pct": "Margin %"},
                hover_data={"revenue": ":$,.0f", "margin_pct": ":.1f", "return_pct": ":.1f"},
            )
            fig1.update_coloraxes(colorbar_title="Margin %")
            st.plotly_chart(styled_chart(fig1, 420), use_container_width=True)

        with col_r:
            st.markdown('<div class="section-header">Revenue vs Margin Bubble</div>', unsafe_allow_html=True)
            fig2 = px.scatter(
                reg, x="revenue", y="margin_pct",
                size="order_lines", color="market", hover_name="region_name",
                labels={"revenue": "Total Revenue ($)", "margin_pct": "Margin %", "market": "Market"},
                size_max=45,
            )
            fig2.add_hline(y=0, line_dash="dash", line_color="rgba(239,68,68,0.6)",
                           annotation_text="Break-even", annotation_position="right")
            fig2.update_yaxes(ticksuffix="%")
            st.plotly_chart(styled_chart(fig2, 420), use_container_width=True)

        st.markdown('<div class="section-header">Market-level Heatmap</div>', unsafe_allow_html=True)
        market_cat = sql(f"""
            SELECT r.market, p.category,
                   ROUND(SUM(f.profit)*100.0 / NULLIF(SUM(f.net_revenue),0),2) AS margin_pct
            FROM Fact_Sales f
            JOIN Dim_Region  r ON f.region_id  = r.region_id
            JOIN Dim_Product p ON f.product_id = p.product_key
            JOIN Dim_Date    d ON f.date_id    = d.date_id
            WHERE d.year IN {year_filter}
            GROUP BY r.market, p.category
        """)
        if not market_cat.empty:
            pivot = market_cat.pivot(index="market", columns="category", values="margin_pct")
            fig_hm = go.Figure(go.Heatmap(
                z=pivot.values.tolist(),
                x=pivot.columns.tolist(),
                y=pivot.index.tolist(),
                colorscale="RdYlGn",
                zmid=0,
                text=[[f"{v:.1f}%" for v in row] for row in pivot.values],
                texttemplate="%{text}",
                hovertemplate="Market: %{y}<br>Category: %{x}<br>Margin: %{text}<extra></extra>",
                colorbar=dict(title="Margin %"),
            ))
            fig_hm.update_layout(xaxis_title="Category", yaxis_title="Market")
            st.plotly_chart(styled_chart(fig_hm, 320), use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — INVENTORY HEALTH
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "Inventory Health":
    st.markdown("## Inventory Health")
    st.markdown(
        "<p style='color:#64748b;font-size:14px;margin-top:-12px;margin-bottom:20px;'>"
        "Underperformer detection · criteria: margin &lt; 5% AND return rate &gt; 15%</p>",
        unsafe_allow_html=True,
    )

    # Highlight planted underperformer
    st.markdown(
        """<div class="alert-banner">
            <div class="alert-title">🚨 Active Supply Chain Alert Detected</div>
            <div class="alert-body">
                <b>Furniture → Tables → South Region</b> has been flagged as
                <b>Underperforming</b>: margin –12.1%, return rate 21.3% (5× baseline),
                average discount 50.1%. Total financial impact: <b>–$11,165</b>.
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    health = sql(f"""
        SELECT r.region_name AS Region, p.category AS Category,
               p.sub_category AS SubCategory,
               ROUND(SUM(f.net_revenue),2)   AS Revenue,
               ROUND(SUM(f.profit),2)         AS Profit,
               ROUND(SUM(f.profit)*100.0 / NULLIF(SUM(f.net_revenue),0),2)          AS Margin_Pct,
               ROUND(AVG(f.discount_pct)*100,2)  AS Avg_Discount,
               ROUND(SUM(CASE WHEN f.returned_flag=1 THEN 1.0 ELSE 0 END) / COUNT(*)*100,2) AS Return_Rate,
               CASE
                   WHEN SUM(f.profit)*1.0 / NULLIF(SUM(f.net_revenue),0) < 0.05
                    AND SUM(CASE WHEN f.returned_flag=1 THEN 1.0 ELSE 0 END) / COUNT(*) > 0.15
                   THEN 'Underperforming'
                   ELSE 'Healthy'
               END AS Status
        FROM Fact_Sales f
        JOIN Dim_Region  r ON f.region_id  = r.region_id
        JOIN Dim_Product p ON f.product_id = p.product_key
        JOIN Dim_Date    d ON f.date_id    = d.date_id
        WHERE d.year IN {year_filter}
          AND p.category IN {cat_filter}
        GROUP BY r.region_name, p.category, p.sub_category
        ORDER BY Margin_Pct ASC, Return_Rate DESC
    """)

    if not health.empty:
        col_l, col_r = st.columns([2, 1])

        with col_l:
            # Colour by status in scatter
            fig_scat = px.scatter(
                health, x="Return_Rate", y="Margin_Pct",
                color="Status",
                color_discrete_map={"Underperforming": "#ef4444", "Healthy": "#10b981"},
                size="Revenue", size_max=38,
                hover_name="SubCategory",
                hover_data={"Region": True, "Category": True,
                            "Revenue": ":$,.0f", "Profit": ":$,.0f",
                            "Return_Rate": ":.1f", "Margin_Pct": ":.1f"},
                labels={"Return_Rate": "Return Rate (%)", "Margin_Pct": "Margin (%)"},
                title="Segment Performance: Return Rate vs Margin %",
            )
            fig_scat.add_vline(x=15, line_dash="dot", line_color="rgba(239,68,68,0.5)",
                               annotation_text="15% return threshold")
            fig_scat.add_hline(y=5, line_dash="dot", line_color="rgba(239,68,68,0.5)",
                               annotation_text="5% margin threshold")
            fig_scat.update_yaxes(ticksuffix="%")
            fig_scat.update_xaxes(ticksuffix="%")
            st.plotly_chart(styled_chart(fig_scat, 440), use_container_width=True)

        with col_r:
            underperf = health[health["Status"] == "Underperforming"]
            healthy   = health[health["Status"] == "Healthy"]
            st.markdown('<div class="section-header">Summary</div>', unsafe_allow_html=True)
            st.markdown(
                f"""<div class="kpi-card returns">
                    <div class="kpi-label">Underperforming Segments</div>
                    <div class="kpi-value" style="color:#f87171;">{len(underperf)}</div>
                    <div class="kpi-delta negative">of {len(health)} total segments</div>
                </div>""",
                unsafe_allow_html=True,
            )
            st.markdown("<br>", unsafe_allow_html=True)
            if not underperf.empty:
                for _, row in underperf.iterrows():
                    st.markdown(
                        f"""<div class="rec-card" style="border-color:rgba(239,68,68,0.3);
                            background:rgba(239,68,68,0.07);">
                            <div class="rec-title" style="color:#fca5a5;">
                                ⚠️ {row['Category']} › {row['SubCategory']}
                            </div>
                            <div class="rec-body">
                                Region: {row['Region']}<br>
                                Margin: {row['Margin_Pct']:.1f}% &nbsp;|&nbsp;
                                Returns: {row['Return_Rate']:.1f}%<br>
                                Discount: {row['Avg_Discount']:.1f}%
                            </div>
                        </div>""",
                        unsafe_allow_html=True,
                    )

        st.markdown('<div class="section-header">Full Segment Data</div>', unsafe_allow_html=True)

        def highlight_row(row):
            c = "background-color: rgba(239,68,68,0.12); color: #fca5a5;" \
                if row["Status"] == "Underperforming" else ""
            return [c] * len(row)

        st.dataframe(
            health.style.apply(highlight_row, axis=1)
                  .format({
                      "Revenue":      "${:,.2f}",
                      "Profit":       "${:,.2f}",
                      "Margin_Pct":   "{:.2f}%",
                      "Avg_Discount": "{:.2f}%",
                      "Return_Rate":  "{:.2f}%",
                  }),
            use_container_width=True,
            height=520,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — STRATEGIC RECOMMENDATIONS
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "Strategic Recommendations":
    st.markdown("## Strategic Recommendations")
    st.markdown(
        "<p style='color:#64748b;font-size:14px;margin-top:-12px;margin-bottom:20px;'>"
        "Data-driven supply chain interventions derived from SQL analysis + DAX validation</p>",
        unsafe_allow_html=True,
    )

    st.markdown(
        """<div class="alert-banner">
            <div class="alert-title">🚨 Critical Finding: Furniture › Tables › South Region</div>
            <div class="alert-body">
                Margin: <b>–12.1%</b> &nbsp;·&nbsp;
                Return Rate: <b>21.3%</b> (5× the 4% dataset baseline) &nbsp;·&nbsp;
                Avg Discount: <b>50.1%</b> &nbsp;·&nbsp;
                Net Profit Impact: <b>–$11,165</b>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    recommendations = [
        (
            "1 · Immediate Discount Freeze",
            "Hard-cap discounting on Tables in the South region (market: LATAM) to a maximum of "
            "<b>15%</b> via the POS/ERP system. The current 50.1% average discount directly "
            "explains the –12% margin — every percentage point of unnecessary discount costs "
            "approximately $223 in net profit for this segment alone.",
        ),
        (
            "2 · Supplier Quality Audit — WoodCraft Furnishings",
            "The 21.3% return rate strongly indicates systematic defects or transit damage on "
            "Tables sourced from WoodCraft Furnishings to South warehouse <code>WH-008</code>. "
            "Initiate a QA audit within 30 days. Benchmark against the 4% dataset baseline "
            "as the acceptance threshold.",
        ),
        (
            "3 · Inventory Rebalancing & Replenishment Freeze",
            "Halt automatic replenishment of affected Table SKUs to <code>WH-008</code> until the "
            "return root cause is identified. Redirect any pending shipments to the East or "
            "West regional warehouses where the same category performs at positive margins.",
        ),
        (
            "4 · Pricing Strategy Review",
            "A 50% average discount applied to a product line that is already at break-even "
            "suggests a flawed promotions strategy or a race-to-zero pricing dynamic with "
            "competitors. Recommend commissioning a price elasticity study before the next "
            "Q1 promotions cycle.",
        ),
    ]

    for title, body in recommendations:
        st.markdown(
            f"""<div class="rec-card">
                <div class="rec-title">{title}</div>
                <div class="rec-body">{body}</div>
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section-header">Segment Profit Waterfall</div>', unsafe_allow_html=True)
    waterfall_data = sql(f"""
        SELECT p.category, p.sub_category,
               ROUND(SUM(f.profit),2) AS profit
        FROM Fact_Sales f
        JOIN Dim_Product p ON f.product_id = p.product_key
        JOIN Dim_Date    d ON f.date_id    = d.date_id
        WHERE d.year IN {year_filter}
        GROUP BY p.category, p.sub_category
        ORDER BY profit ASC
        LIMIT 20
    """)

    if not waterfall_data.empty:
        waterfall_data["label"] = waterfall_data["category"] + " › " + waterfall_data["sub_category"]
        colors = ["#ef4444" if p < 0 else "#10b981" for p in waterfall_data["profit"]]
        fig_wf = go.Figure(go.Bar(
            x=waterfall_data["label"],
            y=waterfall_data["profit"],
            marker_color=colors,
            hovertemplate="<b>%{x}</b><br>Profit: $%{y:,.0f}<extra></extra>",
        ))
        fig_wf.update_layout(
            xaxis_tickangle=-45,
            yaxis_title="Total Profit ($)",
            title="Bottom 20 Sub-Categories by Profit",
        )
        fig_wf.add_hline(y=0, line_dash="solid", line_color="rgba(255,255,255,0.2)")
        st.plotly_chart(styled_chart(fig_wf, 400), use_container_width=True)

    # Methodology note
    st.markdown(
        """<div class="rec-card" style="background:rgba(139,92,246,0.07);
           border-color:rgba(139,92,246,0.25);margin-top:20px;">
            <div class="rec-title" style="color:#c4b5fd;">💡 Methodology Note for Recruiters</div>
            <div class="rec-body">
                The underperforming segment was <b>synthetically injected</b> via
                <code>src/augment_data.py</code> to demonstrate the full analytics lifecycle:
                data engineering → SQL analysis → DAX validation → business recommendations.
                The anomaly was detected independently by three methods:
                raw SQL aggregations, DAX <code>Underperformer Flag</code> measure,
                and this Streamlit dashboard — all returning identical conclusions.
                The original Kaggle Superstore dataset has been scaled from 48K → 100K rows
                via controlled resampling with realistic jitter.
            </div>
        </div>""",
        unsafe_allow_html=True,
    )


# ─── Footer ───────────────────────────────────────────────────────────────────
st.markdown(
    """<hr style='border-color:rgba(255,255,255,0.06);margin-top:40px;'>
    <p style='text-align:center;font-size:11px;color:#475569;padding-bottom:10px;'>
    Enterprise Retail Sales & Supply Chain Analytics &nbsp;·&nbsp;
    Built by Aakash Kumawat &nbsp;·&nbsp;
    <a href='https://github.com/Aakash-Kumawat-621/Enterprise-Sales-Supply-Dashboard'
       style='color:#3b82f6;text-decoration:none;'>GitHub</a>
    </p>""",
    unsafe_allow_html=True,
)
