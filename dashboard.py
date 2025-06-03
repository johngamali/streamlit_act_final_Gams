import streamlit as st
import pandas as pd
import altair as alt
from sqlalchemy import create_engine, text
import numpy as np

# ------------------------
# App Config & Color Palette
# ------------------------
st.set_page_config(page_title="Sales Dashboard", layout="wide")

color_palette = {
    "primary": "#FCF300",
    "secondary": "#FFC600",
    "accent": "#072AC8",
    "highlight": "#1E96FC",
    "background": "#1E96FC"
}

# ------------------------
# DB Connection
# ------------------------
warehouse = "postgresql://etl_db2_whqw_user:P6gBaF2UE64C0Qt8INJghoMpfhZYKTbN@dpg-d0uvtv15pdvs73fvcl5g-a.singapore-postgres.render.com/etl_db2_whqw"
engine = create_engine(warehouse, client_encoding='utf8')
connection = engine.connect()

# ------------------------
# Load Data
# ------------------------
@st.cache_data
def load_data():
    query = """
        SELECT "Order ID", "Product", "Quantity Ordered", "Price Each", "Order Date",
               "Order Year", "Order Month", "Order Month Name", "City", "Country"
        FROM cleaned"""
    result = connection.execute(text(query))
    return pd.DataFrame(result.mappings().all())

df = load_data()
df["Quantity Ordered"] = pd.to_numeric(df["Quantity Ordered"], errors="coerce")
df["Sales"] = df["Quantity Ordered"] * df["Price Each"]

# ------------------------
# Sidebar Filters
# ------------------------
with st.sidebar:
    with st.container():
        st.header("Filter Data")
        years = sorted(df["Order Year"].dropna().unique())
        months = sorted(df["Order Month"].dropna().unique())
        cities = sorted(df["City"].dropna().unique())

        selected_months = st.multiselect("Select Month(s)", months, default=months)
        selected_cities = st.multiselect("Select City/Cities", cities, default=cities)

filtered_df = df[
    (df["Order Month"].isin(selected_months)) &
    (df["City"].isin(selected_cities))
]

# ------------------------
# KPI Metrics
# ------------------------
with st.container():
    st.title("Sales Dashboard")
    st.markdown("Gain insights into product performance across time and geography.")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Orders", f"{filtered_df['Order ID'].nunique():,}")
    col2.metric("Total Revenue", f"${filtered_df['Sales'].sum():,.2f}")
    col3.metric("Cities Covered", filtered_df['City'].nunique())

# ------------------------
# Two-Column Layout for Charts
# ------------------------
left_col, right_col = st.columns(2)

# ------------------------
# Top Products Sold
# ------------------------
with left_col:
    with st.container():
        st.subheader("Top 10 Products Sold")
        top_products = (
            filtered_df.groupby("Product")["Quantity Ordered"]
            .sum()
            .sort_values(ascending=False)
            .head(10)
            .reset_index()
        )
        product_chart = alt.Chart(top_products).mark_bar(color=color_palette["primary"]).encode(
            x=alt.X("Quantity Ordered:Q", title="Total Quantity Sold"),
            y=alt.Y("Product:N", sort="-x", title="Product"),
            tooltip=["Product", "Quantity Ordered"]
        ).properties(width=350, height=300)
        st.altair_chart(product_chart, use_container_width=True)

# ------------------------
# Revenue by Product
# ------------------------
with right_col:
    with st.container():
        st.subheader("Revenue by Product")
        product_revenue = (
            filtered_df.groupby("Product")["Sales"]
            .sum()
            .sort_values(ascending=False)
            .head(10)
            .reset_index()
        )
        revenue_chart = alt.Chart(product_revenue).mark_bar(color=color_palette["secondary"]).encode(
            x=alt.X("Sales:Q", title="Total Revenue"),
            y=alt.Y("Product:N", sort="-x", title="Product"),
            tooltip=["Product", "Sales"]
        ).properties(width=350, height=300)
        st.altair_chart(revenue_chart, use_container_width=True)

# ------------------------
# Top Cities by Sales
# ------------------------
with left_col:
    with st.container():
        st.subheader("Top 10 Cities by Sales")
        top_cities = (
            filtered_df.groupby("City")["Sales"]
            .sum()
            .sort_values(ascending=False)
            .head(10)
            .reset_index()
        )
        city_chart = alt.Chart(top_cities).mark_bar(color=color_palette["highlight"]).encode(
            x=alt.X("Sales:Q", title="Total Revenue"),
            y=alt.Y("City:N", sort="-x", title="City"),
            tooltip=["City", "Sales"]
        ).properties(width=350, height=300)
        st.altair_chart(city_chart, use_container_width=True)

# ------------------------
# Pie Chart by Country
# ------------------------
with right_col:
    with st.container():
        st.subheader("Total Sales by Country")
        country_sales = (
            filtered_df.groupby("Country")["Sales"]
            .sum()
            .reset_index()
            .sort_values("Sales", ascending=False)
        )
        total_sales = country_sales["Sales"].sum()
        country_sales["Percentage"] = country_sales["Sales"] / total_sales * 100
        country_sales["Label"] = country_sales.apply(
            lambda row: f"{row['Country']}: ${row['Sales']:,.0f} ({row['Percentage']:.1f}%)", axis=1
        )
        country_sales["Angle"] = country_sales["Sales"] / total_sales * 2 * np.pi
        country_sales["Cumulative"] = country_sales["Angle"].cumsum() - country_sales["Angle"] / 2
        country_sales["X"] = np.cos(country_sales["Cumulative"]) * 1.2
        country_sales["Y"] = np.sin(country_sales["Cumulative"]) * 1.2

        pie_chart = alt.Chart(country_sales).mark_arc(innerRadius=50).encode(
            theta=alt.Theta(field="Sales", type="quantitative"),
            color=alt.Color("Country:N", scale=alt.Scale(scheme='category10'), legend=alt.Legend(title="Country")),
            tooltip=["Country", "Sales", "Percentage"]
        )
        labels = alt.Chart(country_sales).mark_text(align="center", fontSize=13).encode(
            x=alt.X("X:Q", axis=None),
            y=alt.Y("Y:Q", axis=None),
            text=alt.Text("Label:N"),
            color=alt.value("black")
        )
        pie_combined = (pie_chart + labels).properties(width=400, height=400, title="Sales Distribution by Country")
        st.altair_chart(pie_combined, use_container_width=True)

# ------------------------
# Monthly Sales Trend
# ------------------------
with st.container():
    st.subheader("Monthly Sales Trend")
    monthly_sales = (
        filtered_df.groupby(["Order Year", "Order Month", "Order Month Name"])["Sales"]
        .sum()
        .reset_index()
        .sort_values(["Order Year", "Order Month"])
    )
    monthly_sales["Label"] = monthly_sales["Order Year"].astype(str) + " - " + monthly_sales["Order Month Name"]
    line_chart = alt.Chart(monthly_sales).mark_line(point=True, color=color_palette["accent"]).encode(
        x=alt.X("Label", sort=None, axis=alt.Axis(labelAngle=0, title="Month")),
        y=alt.Y("Sales", title="Total Sales"),
        tooltip=["Order Year", "Order Month Name", "Sales"]
    ).properties(width=700, height=400, title="Monthly Sales Trend")
    st.altair_chart(line_chart, use_container_width=True)

# ------------------------
# Data Table
# ------------------------
with st.container():
    st.subheader("Filtered Data Preview")
    st.dataframe(filtered_df.head(20), use_container_width=True)
    st.markdown("\U0001F6C8 Data is filtered based on the selected month(s) and city/cities.")