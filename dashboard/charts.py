import altair as alt
import pandas as pd
import numpy as np
from typing import Optional, List, Dict

# Institutional, restrained editorial color mapping
BRAND_COLORS = {
    "baccabucci": "#1e40af",   # Deep Blue
    "neemans": "#065f46",      # Deep Pine / Forest Green
    "elevarsports": "#92400e", # Muted Amber / Russet
    "plaeto": "#5b21b6"        # Deep Indigo
}

BRAND_DISPLAY_NAMES = {
    "baccabucci": "Bacca Bucci",
    "neemans": "Neeman's",
    "elevarsports": "Elevar Sports",
    "plaeto": "Plaeto"
}

CATEGORY_COLORS = {
    "Sneakers": "#1e40af",
    "Running/Athletic": "#0284c7",
    "Boots": "#334155",
    "Flip Flop/Slide": "#0d9488",
    "Slip-on/Loafer": "#d97706",
    "Formal/School": "#6d28d9",
    "Casual/Other": "#94a3b8"
}

def get_brand_color(brand_id: str, selected_brand_id: Optional[str] = None) -> str:
    """Returns color based on selection status."""
    if selected_brand_id and selected_brand_id != "all":
        return BRAND_COLORS.get(brand_id, "#1e40af") if brand_id == selected_brand_id else "#cbd5e1"
    return BRAND_COLORS.get(brand_id, "#334155")

def build_catalog_scale_chart(df: pd.DataFrame, metric: str = "active_sku_count", selected_brand: Optional[str] = None) -> alt.Chart:
    """
    Builds a compact horizontal bar chart comparing catalog scale across brands.
    metric: 'active_sku_count' or 'active_product_count'
    """
    df_plot = df.copy()
    metric_label = "Active SKUs (Variants)" if metric == "active_sku_count" else "Active Product Styles"
    
    if selected_brand and selected_brand != "all":
        df_plot["color_category"] = df_plot["brand_id"].apply(lambda b: "Selected" if b == selected_brand else "Cohort")
        color_scale = alt.Scale(domain=["Selected", "Cohort"], range=[BRAND_COLORS.get(selected_brand, "#1e40af"), "#cbd5e1"])
        color_encoding = alt.Color("color_category:N", scale=color_scale, legend=None)
    else:
        color_scale = alt.Scale(domain=list(BRAND_COLORS.keys()), range=list(BRAND_COLORS.values()))
        color_encoding = alt.Color("brand_id:N", scale=color_scale, legend=None)

    bars = alt.Chart(df_plot).mark_bar(cornerRadius=2, height=22).encode(
        y=alt.Y("brand_name:N", title=None, sort="-x", axis=alt.Axis(labelFontSize=11, labelColor="#1e293b")),
        x=alt.X(f"{metric}:Q", title=metric_label, axis=alt.Axis(grid=True, format="," if metric == "active_sku_count" else "d", titleFontSize=11, labelFontSize=10)),
        color=color_encoding,
        tooltip=[
            alt.Tooltip("brand_name:N", title="Brand"),
            alt.Tooltip(f"{metric}:Q", title=metric_label, format=","),
            alt.Tooltip("variant_density:Q", title="Variant Density", format=".2f")
        ]
    )

    text = bars.mark_text(
        align="left",
        baseline="middle",
        dx=6,
        fontSize=11,
        fontWeight=600,
        color="#334155"
    ).encode(
        text=alt.Text(f"{metric}:Q", format=",")
    )

    chart = (bars + text).properties(
        title=alt.TitleParams(
            text=f"Catalog Scale: {metric_label}",
            subtitle="Storefront snapshot (2026-09-29); total purchasable listings",
            fontSize=13,
            fontWeight="bold",
            color="#0f172a"
        ),
        height=160
    )
    return chart

def build_variant_density_chart(df: pd.DataFrame, selected_brand: Optional[str] = None) -> alt.Chart:
    """
    Builds a bar chart of variant density (SKUs per style) with cohort median reference line.
    """
    df_plot = df.copy()
    cohort_med = float(np.nanmedian(df_plot["variant_density"]))

    if selected_brand and selected_brand != "all":
        df_plot["color_category"] = df_plot["brand_id"].apply(lambda b: "Selected" if b == selected_brand else "Cohort")
        color_scale = alt.Scale(domain=["Selected", "Cohort"], range=[BRAND_COLORS.get(selected_brand, "#1e40af"), "#cbd5e1"])
        color_encoding = alt.Color("color_category:N", scale=color_scale, legend=None)
    else:
        color_scale = alt.Scale(domain=list(BRAND_COLORS.keys()), range=list(BRAND_COLORS.values()))
        color_encoding = alt.Color("brand_id:N", scale=color_scale, legend=None)

    bars = alt.Chart(df_plot).mark_bar(cornerRadius=2, size=30).encode(
        x=alt.X("brand_name:N", title=None, sort="-y", axis=alt.Axis(labelFontSize=11, labelColor="#1e293b")),
        y=alt.Y("variant_density:Q", title="Variants per Style", axis=alt.Axis(grid=True, titleFontSize=11, labelFontSize=10)),
        color=color_encoding,
        tooltip=[
            alt.Tooltip("brand_name:N", title="Brand"),
            alt.Tooltip("variant_density:Q", title="Variant Density", format=".2f"),
            alt.Tooltip("active_sku_count:Q", title="Active SKUs", format=","),
            alt.Tooltip("active_product_count:Q", title="Active Products", format=",")
        ]
    )

    text = bars.mark_text(
        align="center",
        baseline="bottom",
        dy=-4,
        fontSize=11,
        fontWeight=600,
        color="#334155"
    ).encode(
        text=alt.Text("variant_density:Q", format=".2f")
    )

    rule_df = pd.DataFrame([{"val": cohort_med}])
    rule = alt.Chart(rule_df).mark_rule(color="#475569", strokeDash=[4, 4], strokeWidth=1.5).encode(
        y="val:Q"
    )

    chart = (bars + text + rule).properties(
        title=alt.TitleParams(
            text="Variant Density (SKUs / Style)",
            subtitle=f"Cohort median: {cohort_med:.2f} variants/style (dashed rule)",
            fontSize=13,
            fontWeight="bold",
            color="#0f172a"
        ),
        height=200
    )
    return chart

def build_price_positioning_chart(df: pd.DataFrame, selected_brand: Optional[str] = None) -> alt.Chart:
    """
    Builds a bar chart of Price Positioning Index with reference line at 1.00.
    """
    df_plot = df.copy()

    if selected_brand and selected_brand != "all":
        df_plot["color_category"] = df_plot["brand_id"].apply(lambda b: "Selected" if b == selected_brand else "Cohort")
        color_scale = alt.Scale(domain=["Selected", "Cohort"], range=[BRAND_COLORS.get(selected_brand, "#1e40af"), "#cbd5e1"])
        color_encoding = alt.Color("color_category:N", scale=color_scale, legend=None)
    else:
        color_scale = alt.Scale(domain=list(BRAND_COLORS.keys()), range=list(BRAND_COLORS.values()))
        color_encoding = alt.Color("brand_id:N", scale=color_scale, legend=None)

    bars = alt.Chart(df_plot).mark_bar(cornerRadius=2, size=30).encode(
        x=alt.X("brand_name:N", title=None, sort="-y", axis=alt.Axis(labelFontSize=11, labelColor="#1e293b")),
        y=alt.Y("price_positioning_index:Q", title="Price Positioning Index (PPI)", scale=alt.Scale(domain=[0, 1.5]), axis=alt.Axis(grid=True, titleFontSize=11, labelFontSize=10)),
        color=color_encoding,
        tooltip=[
            alt.Tooltip("brand_name:N", title="Brand"),
            alt.Tooltip("price_positioning_index:Q", title="PPI", format=".2f"),
            alt.Tooltip("price_median_inr:Q", title="Median Listed Price", format="₹,.0f")
        ]
    )

    text = bars.mark_text(
        align="center",
        baseline="bottom",
        dy=-4,
        fontSize=11,
        fontWeight=600,
        color="#334155"
    ).encode(
        text=alt.Text("price_positioning_index:Q", format=".2f")
    )

    rule_df = pd.DataFrame([{"val": 1.0}])
    rule = alt.Chart(rule_df).mark_rule(color="#475569", strokeDash=[4, 4], strokeWidth=1.5).encode(
        y="val:Q"
    )

    chart = (bars + text + rule).properties(
        title=alt.TitleParams(
            text="Listed Price Positioning Index",
            subtitle="1.00 = cohort median (₹1,899.00); >1.0 premium, <1.0 value",
            fontSize=13,
            fontWeight="bold",
            color="#0f172a"
        ),
        height=200
    )
    return chart

def build_price_median_bar_chart(df: pd.DataFrame, selected_brand: Optional[str] = None) -> alt.Chart:
    """
    Builds a bar chart of Median Listed Selling Price with cohort median reference line.
    """
    df_plot = df.copy()
    cohort_med = float(np.nanmedian(df_plot["price_median_inr"]))

    if selected_brand and selected_brand != "all":
        df_plot["color_category"] = df_plot["brand_id"].apply(lambda b: "Selected" if b == selected_brand else "Cohort")
        color_scale = alt.Scale(domain=["Selected", "Cohort"], range=[BRAND_COLORS.get(selected_brand, "#1e40af"), "#cbd5e1"])
        color_encoding = alt.Color("color_category:N", scale=color_scale, legend=None)
    else:
        color_scale = alt.Scale(domain=list(BRAND_COLORS.keys()), range=list(BRAND_COLORS.values()))
        color_encoding = alt.Color("brand_id:N", scale=color_scale, legend=None)

    bars = alt.Chart(df_plot).mark_bar(cornerRadius=2, size=30).encode(
        x=alt.X("brand_name:N", title=None, sort="-y", axis=alt.Axis(labelFontSize=11, labelColor="#1e293b")),
        y=alt.Y("price_median_inr:Q", title="Median Price (INR)", axis=alt.Axis(grid=True, titleFontSize=11, labelFontSize=10)),
        color=color_encoding,
        tooltip=[
            alt.Tooltip("brand_name:N", title="Brand"),
            alt.Tooltip("price_median_inr:Q", title="Median Price", format="₹,.0f"),
            alt.Tooltip("price_positioning_index:Q", title="PPI", format=".2f")
        ]
    )

    text = bars.mark_text(
        align="center",
        baseline="bottom",
        dy=-4,
        fontSize=11,
        fontWeight=600,
        color="#334155"
    ).encode(
        text=alt.Text("price_median_inr:Q", format="₹,.0f")
    )

    rule_df = pd.DataFrame([{"val": cohort_med}])
    rule = alt.Chart(rule_df).mark_rule(color="#475569", strokeDash=[4, 4], strokeWidth=1.5).encode(
        y="val:Q"
    )

    chart = (bars + text + rule).properties(
        title=alt.TitleParams(
            text="Median Listed Selling Price",
            subtitle=f"Cohort median: ₹{cohort_med:,.0f} (dashed rule)",
            fontSize=13,
            fontWeight="bold",
            color="#0f172a"
        ),
        height=200
    )
    return chart

def build_discount_dual_chart(df: pd.DataFrame, selected_brand: Optional[str] = None) -> alt.Chart:
    """
    Displays Discounted Catalog Ratio and Median Discount Depth side by side in a compact layout.
    """
    df_plot = df[["brand_id", "brand_name", "discounted_catalog_ratio", "median_discount_depth_pct"]].copy()
    df_melted = df_plot.melt(
        id_vars=["brand_id", "brand_name"],
        value_vars=["discounted_catalog_ratio", "median_discount_depth_pct"],
        var_name="metric",
        value_name="percentage"
    )
    metric_names = {
        "discounted_catalog_ratio": "Discounted Catalog %",
        "median_discount_depth_pct": "Median Markdown %"
    }
    df_melted["metric_label"] = df_melted["metric"].map(metric_names)

    chart = alt.Chart(df_melted).mark_bar(cornerRadius=2).encode(
        x=alt.X("metric_label:N", title=None, axis=alt.Axis(labels=True, labelFontSize=10, labelColor="#334155")),
        y=alt.Y("percentage:Q", title="Percentage (%)", scale=alt.Scale(domain=[0, 105]), axis=alt.Axis(grid=True, titleFontSize=11, labelFontSize=10)),
        color=alt.Color("metric_label:N", scale=alt.Scale(range=["#1e40af", "#d97706"]), legend=alt.Legend(title=None, orient="top", labelFontSize=11)),
        column=alt.Column("brand_name:N", title=None, spacing=12, header=alt.Header(labelFontSize=11, labelFontWeight="bold")),
        tooltip=[
            alt.Tooltip("brand_name:N", title="Brand"),
            alt.Tooltip("metric_label:N", title="Promotional Metric"),
            alt.Tooltip("percentage:Q", title="Value (%)", format=".1f")
        ]
    ).properties(
        title=alt.TitleParams(
            text="Promotional Penetration vs Markdown Depth",
            subtitle="Discounted Catalog %: active SKUs with compare_at > selling | Depth: median markdown among discounted SKUs",
            fontSize=13,
            fontWeight="bold",
            color="#0f172a"
        ),
        height=190,
        width=100
    )
    return chart

def build_price_distribution_chart(df_quantiles: pd.DataFrame, selected_brand: Optional[str] = None) -> alt.Chart:
    """
    Builds an analytical percentile range chart showing P25, Median, P75, Min and Max.
    """
    df_plot = df_quantiles.copy()
    df_plot["brand_name"] = df_plot["brand_id"].map(BRAND_DISPLAY_NAMES).fillna(df_plot["brand_id"])

    iqr_bars = alt.Chart(df_plot).mark_bar(size=30, color="#64748b", opacity=0.75, cornerRadius=2).encode(
        x=alt.X("brand_name:N", title=None, sort=["Bacca Bucci", "Plaeto", "Neeman's", "Elevar Sports"], axis=alt.Axis(labelFontSize=11, labelColor="#1e293b")),
        y=alt.Y("price_p25:Q", title="Listed Selling Price (INR)", scale=alt.Scale(zero=False), axis=alt.Axis(grid=True, titleFontSize=11, labelFontSize=10)),
        y2="price_p75:Q",
        tooltip=[
            alt.Tooltip("brand_name:N", title="Brand"),
            alt.Tooltip("price_min:Q", title="Min Price", format="₹,.0f"),
            alt.Tooltip("price_p25:Q", title="25th Percentile", format="₹,.0f"),
            alt.Tooltip("price_median:Q", title="Median Price", format="₹,.0f"),
            alt.Tooltip("price_p75:Q", title="75th Percentile", format="₹,.0f"),
            alt.Tooltip("price_max:Q", title="Max Price", format="₹,.0f"),
            alt.Tooltip("price_iqr:Q", title="Price IQR", format="₹,.0f")
        ]
    )

    median_ticks = alt.Chart(df_plot).mark_tick(size=30, thickness=3, color="#0f172a").encode(
        x=alt.X("brand_name:N"),
        y="price_median:Q"
    )

    chart = (iqr_bars + median_ticks).properties(
        title=alt.TitleParams(
            text="Listed Price Distribution (P25 — Median — P75)",
            subtitle="Current storefront snapshot; not sales-weighted transaction prices.",
            fontSize=13,
            fontWeight="bold",
            color="#0f172a"
        ),
        height=220
    )
    return chart

def build_assortment_scatter_chart(df: pd.DataFrame) -> alt.Chart:
    """
    Scatter plot: Active Products (X) vs Active SKUs (Y) with brand labels.
    """
    df_plot = df.copy()
    color_scale = alt.Scale(domain=list(BRAND_COLORS.keys()), range=list(BRAND_COLORS.values()))

    points = alt.Chart(df_plot).mark_circle(size=120, opacity=0.9).encode(
        x=alt.X("active_product_count:Q", title="Active Product Styles (Breadth)", axis=alt.Axis(grid=True, titleFontSize=11, labelFontSize=10)),
        y=alt.Y("active_sku_count:Q", title="Active SKUs (Variant Depth)", axis=alt.Axis(grid=True, format=",", titleFontSize=11, labelFontSize=10)),
        color=alt.Color("brand_id:N", scale=color_scale, legend=None),
        tooltip=[
            alt.Tooltip("brand_name:N", title="Brand"),
            alt.Tooltip("active_product_count:Q", title="Styles", format=","),
            alt.Tooltip("active_sku_count:Q", title="SKUs", format=","),
            alt.Tooltip("variant_density:Q", title="Variants/Style", format=".2f")
        ]
    )

    text = points.mark_text(
        align="left",
        baseline="middle",
        dx=9,
        fontSize=11,
        fontWeight=600,
        color="#1e293b"
    ).encode(
        text=alt.Text("brand_name:N")
    )

    chart = (points + text).properties(
        title=alt.TitleParams(
            text="Assortment Architecture: Breadth vs Depth",
            subtitle="Descriptive positioning: parent styles vs total purchasable SKU variants",
            fontSize=13,
            fontWeight="bold",
            color="#0f172a"
        ),
        height=220
    )
    return chart

def build_discount_scatter_chart(df: pd.DataFrame) -> alt.Chart:
    """
    Scatter plot: Discounted Catalog Ratio (X) vs Median Discount Depth (Y).
    Strictly descriptive; NO regression line or correlation display.
    """
    df_plot = df.copy()
    color_scale = alt.Scale(domain=list(BRAND_COLORS.keys()), range=list(BRAND_COLORS.values()))

    points = alt.Chart(df_plot).mark_circle(size=120, opacity=0.9).encode(
        x=alt.X("discounted_catalog_ratio:Q", title="Discounted Catalog Ratio (%)", scale=alt.Scale(domain=[35, 105]), axis=alt.Axis(grid=True, titleFontSize=11, labelFontSize=10)),
        y=alt.Y("median_discount_depth_pct:Q", title="Median Markdown Depth (%)", scale=alt.Scale(domain=[10, 65]), axis=alt.Axis(grid=True, titleFontSize=11, labelFontSize=10)),
        color=alt.Color("brand_id:N", scale=color_scale, legend=None),
        tooltip=[
            alt.Tooltip("brand_name:N", title="Brand"),
            alt.Tooltip("discounted_catalog_ratio:Q", title="Discounted Catalog", format=".1f", formatType="number"),
            alt.Tooltip("median_discount_depth_pct:Q", title="Median Markdown Depth", format=".1f", formatType="number")
        ]
    )

    text = points.mark_text(
        align="left",
        baseline="middle",
        dx=9,
        fontSize=11,
        fontWeight=600,
        color="#1e293b"
    ).encode(
        text=alt.Text("brand_name:N")
    )

    chart = (points + text).properties(
        title=alt.TitleParams(
            text="Promotional Breadth vs Depth",
            subtitle="Descriptive comparison; compare_at_price does not prove realized transaction savings",
            fontSize=13,
            fontWeight="bold",
            color="#0f172a"
        ),
        height=220
    )
    return chart

def build_category_mix_chart(df_cat_mix: pd.DataFrame) -> alt.Chart:
    """
    Stacked horizontal bar chart of standardized category shares.
    """
    df_plot = df_cat_mix.copy()
    df_plot["brand_name"] = df_plot["brand_id"].map(BRAND_DISPLAY_NAMES).fillna(df_plot["brand_id"])

    color_scale = alt.Scale(
        domain=list(CATEGORY_COLORS.keys()),
        range=list(CATEGORY_COLORS.values())
    )

    chart = alt.Chart(df_plot).mark_bar(cornerRadius=1).encode(
        y=alt.Y("brand_name:N", title=None, sort=["Bacca Bucci", "Neeman's", "Plaeto", "Elevar Sports"], axis=alt.Axis(labelFontSize=11, labelColor="#1e293b")),
        x=alt.X("category_share_pct:Q", title="Share of Catalog SKUs (%)", scale=alt.Scale(domain=[0, 100]), axis=alt.Axis(grid=True, titleFontSize=11, labelFontSize=10)),
        color=alt.Color("category_std:N", scale=color_scale, title="Category", legend=alt.Legend(orient="bottom", columns=4, labelFontSize=10, titleFontSize=11)),
        tooltip=[
            alt.Tooltip("brand_name:N", title="Brand"),
            alt.Tooltip("category_std:N", title="Category"),
            alt.Tooltip("category_sku_count:Q", title="SKUs", format=","),
            alt.Tooltip("category_share_pct:Q", title="Share (%)", format=".1f")
        ]
    ).properties(
        title=alt.TitleParams(
            text="Standardized Assortment Category Mix",
            subtitle="Share of active SKUs per standardized category (storefront snapshot 2026-09-29)",
            fontSize=13,
            fontWeight="bold",
            color="#0f172a"
        ),
        height=170
    )
    return chart

def build_search_trends_chart(df_search_series: pd.DataFrame, selected_brand: Optional[str] = None) -> alt.Chart:
    """
    53-week Google Trends line chart.
    Handles <1 properly by plotting only numeric observations without converting <1 to 0.
    """
    df_plot = df_search_series.copy()
    df_plot["brand_name"] = df_plot["brand_id"].map(BRAND_DISPLAY_NAMES).fillna(df_plot["brand_id"])

    numeric_df = df_plot.dropna(subset=["relative_search_interest"]).copy()

    color_scale = alt.Scale(domain=list(BRAND_DISPLAY_NAMES.values()), range=[BRAND_COLORS[b] for b in BRAND_DISPLAY_NAMES])

    lines = alt.Chart(numeric_df).mark_line(strokeWidth=2.0, interpolate="monotone").encode(
        x=alt.X("week_start_date:T", title="Week Starting", axis=alt.Axis(format="%b %Y", grid=True, titleFontSize=11, labelFontSize=10)),
        y=alt.Y("relative_search_interest:Q", title="Relative Search Interest (0-100)", scale=alt.Scale(domain=[0, 105]), axis=alt.Axis(grid=True, titleFontSize=11, labelFontSize=10)),
        color=alt.Color("brand_name:N", scale=color_scale, legend=alt.Legend(title=None, orient="top", labelFontSize=11)),
        tooltip=[
            alt.Tooltip("brand_name:N", title="Brand"),
            alt.Tooltip("week_str:N", title="Week"),
            alt.Tooltip("relative_search_interest:Q", title="Relative Search Interest", format="d")
        ]
    )

    points = alt.Chart(numeric_df).mark_circle(size=20).encode(
        x="week_start_date:T",
        y="relative_search_interest:Q",
        color="brand_name:N"
    )

    chart = (lines + points).properties(
        title=alt.TitleParams(
            text="Google Trends: 53-Week Relative Search Interest (India, Web Search)",
            subtitle="Values indexed [0-100] relative to peak search attention; low volume (<1) preserved as breaks",
            fontSize=13,
            fontWeight="bold",
            color="#0f172a"
        ),
        height=260
    )
    return chart

def build_cohort_search_share_chart(df_search_series: pd.DataFrame) -> alt.Chart:
    """
    Stacked area or multi-line chart for the 50 comparable weeks where all 4 brands have complete data.
    """
    comp_df = df_search_series.dropna(subset=["cohort_relative_search_share"]).copy()
    comp_df["brand_name"] = comp_df["brand_id"].map(BRAND_DISPLAY_NAMES).fillna(comp_df["brand_id"])

    color_scale = alt.Scale(domain=list(BRAND_DISPLAY_NAMES.values()), range=[BRAND_COLORS[b] for b in BRAND_DISPLAY_NAMES])

    chart = alt.Chart(comp_df).mark_area(opacity=0.65).encode(
        x=alt.X("week_start_date:T", title="Week Starting", axis=alt.Axis(format="%b %Y", grid=True, titleFontSize=11, labelFontSize=10)),
        y=alt.Y("cohort_relative_search_share:Q", title="Cohort Search Share (%)", stack="zero", scale=alt.Scale(domain=[0, 100]), axis=alt.Axis(grid=True, titleFontSize=11, labelFontSize=10)),
        color=alt.Color("brand_name:N", scale=color_scale, legend=alt.Legend(title=None, orient="top", labelFontSize=11)),
        tooltip=[
            alt.Tooltip("brand_name:N", title="Brand"),
            alt.Tooltip("week_str:N", title="Week"),
            alt.Tooltip("cohort_relative_search_share:Q", title="Cohort Search Share", format=".1f")
        ]
    ).properties(
        title=alt.TitleParams(
            text="Cohort Relative Search Share (50 Comparable Weeks)",
            subtitle="Share of relative search attention within this four-brand cohort; not footwear market share.",
            fontSize=13,
            fontWeight="bold",
            color="#0f172a"
        ),
        height=230
    )
    return chart
