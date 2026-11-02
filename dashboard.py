import streamlit as st
import requests
import pandas as pd
import plotly.express as px

API = "http://127.0.0.1:8000"

st.set_page_config(page_title="Retail Analytics", layout="wide")
st.title("📊 Retail Analytics & Reconciliation Dashboard")

# --- One fetch that returns a DataFrame ---
def fetch(path, params=None):
    try:
        r = requests.get(f"{API}{path}", params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict):
            return pd.DataFrame([data])
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Failed to fetch {path}: {e}")
        return pd.DataFrame()

# --- Create all tabs FIRST ---
tab_overview, tab_exceptions, tab_rules, tab_runs, \
tab_portfolio, tab_sales, tab_stores, tab_seasonal = st.tabs([
    "Overview", "Exceptions", "By Rule", "Run History",
    "Portfolio", "Sales & Margins", "Stores", "Seasonality"
])

# ============ OVERVIEW (reconciliation KPIs) ============
with tab_overview:
    o = fetch("/api/overview")
    if not o.empty:
        row = o.iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Exceptions", int(row["total_exceptions"]))
        c2.metric("Open", int(row["open_exceptions"]))
        c3.metric("Resolved", int(row["resolved_exceptions"]))
        c4.metric("Open at Risk", f"{row['open_at_risk']:,.2f}")

    st.divider()
    rule_data = fetch("/api/exceptions/by-rule")
    if not rule_data.empty:
        fig = px.bar(rule_data, x="rule_code", y="total_at_risk",
                     text="count", title="Total At Risk by Rule")
        st.plotly_chart(fig, use_container_width=True)

# ============ EXCEPTIONS ============
with tab_exceptions:
    rules_df = fetch("/api/exceptions/by-rule")
    rule_options = ["All"] + rules_df["rule_code"].tolist() if not rules_df.empty else ["All"]
    col1, col2 = st.columns(2)
    rule_filter = col1.selectbox("Filter by rule", rule_options)
    status_filter = col2.selectbox("Filter by status", ["All", "open", "resolved"])

    params = {}
    if rule_filter != "All": params["rule_code"] = rule_filter
    if status_filter != "All": params["status"] = status_filter

    rows = fetch("/api/exceptions", params)
    if not rows.empty:
        st.dataframe(rows, use_container_width=True, hide_index=True)

        st.subheader("Resolve an exception")
        exc_id = st.selectbox("Exception ID", rows["exception_id"].tolist())
        resolved_by = st.text_input("Resolved by")
        note = st.text_area("Resolution note")
        if st.button("Mark as resolved") and resolved_by:
            r = requests.post(f"{API}/api/exceptions/{exc_id}/resolve",
                              json={"resolved_by": resolved_by, "resolution_note": note})
            if r.ok:
                st.success(f"Exception {exc_id} resolved.")
                st.rerun()
            else:
                st.error(r.text)
    else:
        st.info("No exceptions match the filter.")

# ============ BY RULE ============
with tab_rules:
    rule_data = fetch("/api/exceptions/by-rule")
    if not rule_data.empty:
        st.dataframe(rule_data, use_container_width=True, hide_index=True)

# ============ RUN HISTORY ============
with tab_runs:
    runs = fetch("/api/runs")
    if not runs.empty:
        st.dataframe(runs, use_container_width=True, hide_index=True)

# ============ PRODUCT PORTFOLIO ============
with tab_portfolio:
    col1, col2 = st.columns(2)
    with col1:
        abc = fetch("/api/analytics/abc")
        if not abc.empty:
            summary = abc.groupby("abc_class", as_index=False).agg(
                products=("product_id", "count"),
                revenue=("revenue", "sum"))
            fig = px.bar(summary, x="abc_class", y="revenue",
                         color="abc_class", text="products",
                         title="ABC — Revenue by Class")
            st.plotly_chart(fig, use_container_width=True)
    with col2:
        mv = fetch("/api/analytics/margin-volume")
        if not mv.empty:
            fig = px.scatter(mv, x="units_sold", y="margin_pct",
                             hover_data=["product_id", "revenue"],
                             title="Margin % vs. Units Sold")
            st.plotly_chart(fig, use_container_width=True)

# ============ SALES & MARGINS ============
with tab_sales:
    monthly = fetch("/api/analytics/monthly")
    if not monthly.empty:
        monthly["month"] = pd.to_datetime(monthly["month"])
        fig = px.line(monthly, x="month", y=["revenue", "gross_profit"],
                      markers=True, title="Monthly Revenue & Gross Profit")
        st.plotly_chart(fig, use_container_width=True)
        fig2 = px.line(monthly, x="month", y="margin_pct",
                       markers=True, title="Monthly Margin %")
        st.plotly_chart(fig2, use_container_width=True)

    below = fetch("/api/analytics/below-cost")
    if not below.empty:
        st.warning(f"⚠️ {len(below)} below-cost sales — total loss: {below['loss_amount'].sum():,.0f}")
        st.dataframe(below, use_container_width=True, hide_index=True)
    else:
        st.success("✅ No below-cost sales found.")

# ============ STORES ============
with tab_stores:
    stores = fetch("/api/analytics/stores")
    if not stores.empty:
        st.dataframe(stores, use_container_width=True, hide_index=True)
    netrev = fetch("/api/analytics/net-revenue")
    if not netrev.empty:
        fig = px.bar(netrev, x="store_id", y=["gross_revenue", "net_revenue"],
                     barmode="group", title="Gross vs. Net Revenue by Store")
        st.plotly_chart(fig, use_container_width=True)

# ============ SEASONALITY ============
with tab_seasonal:
    col1, col2 = st.columns(2)
    with col1:
        seasonal = fetch("/api/analytics/seasonal")
        if not seasonal.empty:
            fig = px.bar(seasonal, x="month", y="seasonal_index",
                         title="Seasonal Index (1.0 = average)")
            fig.add_hline(y=1.0, line_dash="dash", line_color="gray")
            st.plotly_chart(fig, use_container_width=True)
    with col2:
        yoy = fetch("/api/analytics/yoy")
        if not yoy.empty:
            fig = px.line(yoy, x="month", y=["rev_2018", "rev_2019"],
                          markers=True, title="Year-over-Year Revenue")
            st.plotly_chart(fig, use_container_width=True)