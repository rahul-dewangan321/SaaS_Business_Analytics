"""
app.py
------
Modern, interactive SaaS Business Analytics dashboard.

Stack: Streamlit + Plotly + Pandas + scikit-learn + fpdf
A dark, modern (glassmorphism / neon-slate) theme with:
  * Global interactive filters (country / industry / segment / plan / date)
  * Executive Summary page (KPIs + trend + geography + plan mix)
  * Customer & Subscription page (cohort + retention + churn)
  * Product Usage & Support page (feature adoption + ticket analytics)
  * Predictive Analytics page (churn model + revenue forecast)
  * Export & Reporting page (CSV / Excel / branded PDF)

Run with:  streamlit run app.py
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Local modules
import data_loader as dl
import analytics as an
import styles as stl
import reporting as rep

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="SaaS Business Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(stl.inject_global_css(), unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
data = dl.load_all()
subs = dl.build_customer_subscription()
revenue = dl.build_revenue()
usage = dl.build_usage()
support = dl.build_support()
churn_data = dl.build_churn_dataset()

plans = data["plans"]
plan_price = dict(zip(plans["Plan_Id"], plans["Plan_Name"]))


# ---------------------------------------------------------------------------
# Sidebar: global filters (shared across all pages)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🎛️ Filters")
    st.markdown("Apply global filters to every page below. Downloads respect "
                "these filters too.")

    countries = ["All"] + sorted(data["customers"]["Country"].dropna().unique().tolist())
    industries = ["All"] + sorted(data["customers"]["Industry"].dropna().unique().tolist())
    segments = ["All"] + sorted(data["customers"]["Segment"].dropna().unique().tolist())
    plans_list = ["All"] + plans["Plan_Id"].tolist()

    sel_country = st.multiselect("🌍 Country", countries, default=["All"], help=None)
    sel_industry = st.multiselect("🏭 Industry", industries, default=["All"])
    sel_segment = st.multiselect("👥 Segment", segments, default=["All"])
    sel_plan = st.multiselect("📦 Plan", plans_list, default=["All"], format_func=lambda x: plan_price.get(x, x))

    if "All" in sel_country:
        filter_countries = countries[1:]
    else:
        filter_countries = sel_country
    if "All" in sel_industry:
        filter_industries = industries[1:]
    else:
        filter_industries = sel_industry
    if "All" in sel_segment:
        filter_segments = segments[1:]
    else:
        filter_segments = sel_segment
    if "All" in sel_plan:
        filter_plans = plans_list[1:]
    else:
        filter_plans = sel_plan

    st.markdown("---")
    st.markdown("### 📅 Date Range")
    min_date = pd.to_datetime(revenue["Payment_Date"]).min().date()
    max_date = pd.to_datetime(revenue["Payment_Date"]).max().date()
    date_range = st.date_input(
        "Select period",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = min_date, max_date
    start_date = start_date or min_date
    end_date = end_date or max_date

    st.markdown("---")
    st.markdown("### ℹ️ About")
    st.caption("End-to-End SaaS Business Analytics · built with Streamlit, "
               "Plotly, scikit-learn & Pandas.")


def customer_filter_mask(df: pd.DataFrame) -> pd.Series:
    """Return a boolean mask for customer-level global filters."""
    mask = pd.Series(True, index=df.index)
    if "Country" in df.columns:
        mask &= df["Country"].isin(filter_countries)
    if "Industry" in df.columns:
        mask &= df["Industry"].isin(filter_industries)
    if "Segment" in df.columns:
        mask &= df["Segment"].isin(filter_segments)
    if "Plan_Id" in df.columns:
        mask &= df["Plan_Id"].isin(filter_plans)
    return mask


def apply_filters(df: pd.DataFrame, date_col: str | None = None) -> pd.DataFrame:
    """Apply all global filters to an arbitrary dataframe (with optional date col)."""
    out = df[customer_filter_mask(df)].copy()
    if date_col and date_col in out.columns:
        out = out[
            (out[date_col] >= pd.Timestamp(start_date))
            & (out[date_col] <= pd.Timestamp(end_date) + pd.Timedelta(days=1))
        ]
    return out


# Pre-filtered frames used throughout
revenue_f = apply_filters(revenue, "Payment_Date")
subs_f = apply_filters(subs)
usage_f = apply_filters(usage, "Event_Date")
support_f = apply_filters(support, "Ticket_Date")
churn_f = apply_filters(churn_data)


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------
page = st.sidebar.radio(
    "**Navigate**",
    [
        "📈 Executive Summary",
        "👥 Customer & Subscription",
        "🛠️ Usage & Support",
        "🤖 Predictive Analytics",
        "📤 Export & Report",
    ],
)

# ---------------------------------------------------------------------------
# Shared plot helpers
# ---------------------------------------------------------------------------
def style_fig(fig, height: int = 380):
    fig.update_layout(
        template=stl.PLOTLY_TEMPLATE,
        height=height,
        margin=dict(l=10, r=10, t=45, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=stl.TEXT_COLOR),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def render_kpi_row(kpis: list[dict]):
    cols = st.columns(len(kpis))
    for col, kpi in zip(cols, kpis):
        col.metric(
            label=kpi["label"],
            value=kpi["value"],
            delta=kpi.get("delta"),
            help=kpi.get("help"),
        )


# ===========================================================================
# PAGE 1 - EXECUTIVE SUMMARY
# ===========================================================================
if page == "📈 Executive Summary":
    st.markdown(
        f'<div class="dashboard-title">📊 SaaS Business Analytics</div>'
        f'<div class="dashboard-subtitle">End-to-End analytics · Executive overview · '
        f'{start_date} to {end_date}</div>',
        unsafe_allow_html=True,
    )

    # ---- KPIs ----
    rev_paid = revenue_f[revenue_f["Payment_Status"] == "Paid"]
    churn_rt = an.churn_rate(subs_f)
    kpis = [
        {"label": "Total Customers", "value": f"{an.total_customers(subs_f):,}"},
        {"label": "Total Revenue", "value": f"${an.total_revenue(revenue_f):,.0f}"},
        {"label": "Active Subs", "value": f"{an.active_customers(subs_f):,}"},
        {"label": "Churn Rate", "value": f"{churn_rt:.1f}%"},
        {"label": "Support Tickets", "value": f"{an.total_tickets(support_f):,}"},
        {"label": "Avg Session (min)", "value": f"{an.avg_session_minutes(usage_f):,.0f}"},
    ]
    render_kpi_row(kpis)

    st.markdown("---")

    left, right = st.columns([2, 1])
    with left:
        # Monthly revenue trend
        monthly = (
            revenue_f[revenue_f["Payment_Status"] == "Paid"]
            .groupby(revenue_f["Payment_Date"].dt.to_period("M"))
            .agg(revenue=("Amount", "sum"))
            .reset_index()
        )
        monthly["period"] = monthly["Payment_Date"].astype(str)
        fig = px.area(
            monthly, x="period", y="revenue",
            title="Monthly Revenue Trend",
            color_discrete_sequence=[stl.ACCENT],
        )
        fig.update_traces(fillcolor=stl.ACCENT, line=dict(color=stl.ACCENT_2, width=2))
        st.plotly_chart(style_fig(fig), use_container_width=True)

    with right:
        # Revenue by plan (donut)
        plan_rev = (
            revenue_f[revenue_f["Payment_Status"] == "Paid"]
            .groupby("Plan_Name")["Amount"].sum().reset_index()
        )
        fig = px.pie(
            plan_rev, names="Plan_Name", values="Amount",
            title="Revenue by Plan", hole=0.55,
            color_discrete_sequence=stl.CHART_COLORS,
        )
        fig.update_traces(textinfo="percent+label")
        st.plotly_chart(style_fig(fig, height=330), use_container_width=True)

    # Second row
    left, mid, right = st.columns(3)
    with left:
        # Revenue by country
        c_rev = (
            revenue_f[revenue_f["Payment_Status"] == "Paid"]
            .groupby("Country")["Amount"].sum().sort_values(ascending=True)
            .reset_index()
        )
        fig = px.bar(
            c_rev, x="Amount", y="Country", orientation="h",
            title="Revenue by Country", color="Country",
            color_discrete_sequence=stl.CHART_COLORS,
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(style_fig(fig, height=300), use_container_width=True)

    with mid:
        # Retained vs churned
        status_agg = subs_f["Status"].value_counts().reset_index()
        status_agg.columns = ["status", "count"]
        fig = px.bar(
            status_agg, x="status", y="count", color="status",
            title="Subscription Status Mix", color_discrete_sequence=stl.CHART_COLORS,
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(style_fig(fig, height=300), use_container_width=True)

    with right:
        # Revenue by industry
        i_rev = (
            revenue_f[revenue_f["Payment_Status"] == "Paid"]
            .groupby("Industry")["Amount"].sum().sort_values(ascending=True)
            .tail(6).reset_index()
        )
        fig = px.bar(
            i_rev, x="Amount", y="Industry", orientation="h",
            title="Revenue by Industry", color="Industry",
            color_discrete_sequence=stl.CHART_COLORS,
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(style_fig(fig, height=300), use_container_width=True)

    st.markdown(
        f'<div class="footer-note">Modernized with Streamlit · Data reflects '
        f'{len(revenue_f):,} payments, {len(usage_f):,} usage events & '
        f'{len(support_f):,} tickets.</div>',
        unsafe_allow_html=True,
    )

# ===========================================================================
# PAGE 2 - CUSTOMER & SUBSCRIPTION
# ===========================================================================
elif page == "👥 Customer & Subscription":
    st.markdown(
        f'<div class="dashboard-title">👥 Customer & Subscription Analysis</div>'
        f'<div class="dashboard-subtitle">Cohorts, retention & churn by customer '
        f'characteristics</div>',
        unsafe_allow_html=True,
    )

    active = (subs_f["Status"] == "Active").sum()
    churned = (subs_f["Status"].isin(["Churned", "Cancelled"])).sum()
    total = len(subs_f)
    retention = active / total * 100 if total else 0
    kpis = [
        {"label": "Total Customers", "value": f"{an.total_customers(subs_f):,}"},
        {"label": "Active", "value": f"{active:,}"},
        {"label": "Churned", "value": f"{churned:,}"},
        {"label": "Retention Rate", "value": f"{retention:.1f}%"},
        {"label": "Avg Duration (days)", "value": f"{an.avg_subscription_duration(subs_f):,.0f}"},
    ]
    render_kpi_row(kpis)
    st.markdown("---")

    left, right = st.columns(2)
    with left:
        custom = subs_f["Signup_Date"].copy() if "Signup_Date" in subs_f else subs_f["Start_Date"].copy()
        signups = pd.Series(custom).dt.to_period("M").value_counts().sort_index().reset_index()
        signups.columns = ["period", "count"]
        signups["period"] = signups["period"].astype(str)
        fig = px.bar(signups, x="period", y="count", title="Monthly Customer Signups",
                     color_discrete_sequence=[stl.ACCENT_2])
        st.plotly_chart(style_fig(fig, height=320), use_container_width=True)

    with right:
        size_rev = subs_f.groupby("Company_Size")["Customer_Id"].nunique().reset_index()
        size_rev.columns = ["Company_Size", "count"]
        fig = px.bar(size_rev, x="Company_Size", y="count", title="Customers by Company Size",
                     color="Company_Size", color_discrete_sequence=stl.CHART_COLORS)
        fig.update_layout(showlegend=False)
        st.plotly_chart(style_fig(fig, height=320), use_container_width=True)

    left, mid, right = st.columns(3)
    with left:
        c_country = subs_f.groupby("Country")["Customer_Id"].nunique().reset_index()
        c_country.columns = ["Country", "count"]
        fig = px.bar(c_country, x="Country", y="count", title="Customers by Country",
                     color="Country", color_discrete_sequence=stl.CHART_COLORS)
        fig.update_layout(showlegend=False)
        st.plotly_chart(style_fig(fig, height=300), use_container_width=True)

    with mid:
        seg = subs_f["Segment"].value_counts().reset_index()
        seg.columns = ["Segment", "count"]
        fig = px.bar(seg, x="Segment", y="count", title="Customers by Segment",
                     color="Segment", color_discrete_sequence=stl.CHART_COLORS)
        fig.update_layout(showlegend=False)
        st.plotly_chart(style_fig(fig, height=300), use_container_width=True)

    with right:
        # Churn rate by plan
        churn_by_plan = (
            subs_f.groupby("Plan_Name")["Status"]
            .apply(lambda s: (s.isin(["Churned", "Cancelled"]).sum() / len(s)) * 100)
            .reset_index()
        )
        churn_by_plan.columns = ["Plan", "churn_pct"]
        fig = px.bar(churn_by_plan, x="Plan", y="churn_pct", title="Churn Rate by Plan",
                     color="Plan", color_discrete_sequence=stl.CHART_COLORS)
        fig.update_layout(showlegend=False)
        st.plotly_chart(style_fig(fig, height=300), use_container_width=True)

# ===========================================================================
# PAGE 3 - USAGE & SUPPORT
# ===========================================================================
elif page == "🛠️ Usage & Support":
    st.markdown(
        f'<div class="dashboard-title">🛠️ Product Usage & Support Analysis</div>'
        f'<div class="dashboard-subtitle">Feature adoption, engagement & ticket analytics</div>',
        unsafe_allow_html=True,
    )

    rez = support_f["Resolution_Time"].mean()
    kpis = [
        {"label": "Total Customers(usage)", "value": f"{usage_f['Customer_Id'].nunique():,}"},
        {"label": "Total Tickets", "value": f"{len(support_f):,}"},
        {"label": "Avg Login Count", "value": f"{usage_f['Login_Count'].mean():,.0f}"},
        {"label": "Avg Session (min)", "value": f"{usage_f['Session_Minutes'].mean():,.0f}"},
        {"label": "Avg Resolve Time", "value": f"{rez:,.0f}h" if not np.isnan(rez) else "0h"},
    ]
    render_kpi_row(kpis)
    st.markdown("---")

    left, right = st.columns(2)
    with left:
        usage_m = usage_f.groupby(usage_f["Event_Date"].dt.to_period("M"))["Login_Count"].sum().reset_index()
        usage_m["period"] = usage_m["Event_Date"].astype(str)
        fig = px.line(usage_m, x="period", y="Login_Count", title="Monthly Usage Trend (Logins)",
                      color_discrete_sequence=[stl.ACCENT_5])
        st.plotly_chart(style_fig(fig, height=320), use_container_width=True)

    with right:
        feat = usage_f.groupby("Feature_Name")["Login_Count"].sum().sort_values().reset_index()
        fig = px.bar(feat, x="Login_Count", y="Feature_Name", orientation="h",
                     title="Most Used Features", color="Feature_Name",
                     color_discrete_sequence=stl.CHART_COLORS)
        fig.update_layout(showlegend=False)
        st.plotly_chart(style_fig(fig, height=320), use_container_width=True)

    k1, k2, k3 = st.columns(3)
    with k1:
        s = support_f["Status"].value_counts().reset_index()
        s.columns = ["Status", "count"]
        fig = px.bar(s, x="Status", y="count", title="Ticket Status Distribution",
                     color="Status", color_discrete_sequence=stl.CHART_COLORS)
        fig.update_layout(showlegend=False)
        st.plotly_chart(style_fig(fig, height=300), use_container_width=True)

    with k2:
        cat = support_f["Category"].value_counts().reset_index()
        cat.columns = ["Category", "count"]
        fig = px.bar(cat, x="Category", y="count", title="Tickets by Category",
                     color="Category", color_discrete_sequence=stl.CHART_COLORS)
        fig.update_layout(showlegend=False)
        st.plotly_chart(style_fig(fig, height=300), use_container_width=True)

    with k3:
        pri = support_f["Priority"].value_counts().reset_index()
        pri.columns = ["Priority", "count"]
        fig = px.pie(pri, names="Priority", values="count", title="Tickets by Priority",
                     hole=0.5, color_discrete_sequence=stl.CHART_COLORS)
        fig.update_traces(textinfo="percent")
        st.plotly_chart(style_fig(fig, height=300), use_container_width=True)

# ===========================================================================
# PAGE 4 - PREDICTIVE ANALYTICS
# ===========================================================================
elif page == "🤖 Predictive Analytics":
    st.markdown(
        f'<div class="dashboard-title">🤖 Predictive Analytics</div>'
        f'<div class="dashboard-subtitle">Customer churn model & revenue forecasting '
        f'(trained on filtered data)</div>',
        unsafe_allow_html=True,
    )

    # ---------- Churn model ----------
    with st.spinner("Training churn model..."):
        churn_mask = pd.Series(True, index=churn_f.index)
        if "Country" in churn_f.columns:
            churn_mask &= churn_f["Country"].isin(filter_countries)
        if "Industry" in churn_f.columns:
            churn_mask &= churn_f["Industry"].isin(filter_industries)
        if "Segment" in churn_f.columns:
            churn_mask &= churn_f["Segment"].isin(filter_segments)
        churn_train = churn_f[churn_mask]

        if len(churn_train) >= 30:
            result = an.train_churn_model(churn_train)
        else:
            result = None

    st.markdown("### 🧠 Customer Churn Prediction (Gradient Boosting)")

    if result is None:
        st.warning("Not enough customers with current filters to train the model. "
                   "Broaden your filters to see predictions.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Model Accuracy", f"{result['accuracy']*100:.1f}%")
        c2.metric("AUC Score", f"{result['auc']:.3f}")
        c3.metric("Churned Rate", f"{result['churned_rate']:.1f}%")
        c4.metric("Training Samples", f"{result['n_train']:,}")

        left, right = st.columns(2)
        with left:
            # ROC curve
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=result["fpr"], y=result["tpr"], mode="lines",
                name=f"AUC={result['auc']:.3f}",
                line=dict(color=stl.ACCENT_2, width=2),
            ))
            fig.add_trace(go.Scatter(
                x=[0, 1], y=[0, 1], mode="lines", name="Random",
                line=dict(color=stl.MUTED_COLOR, dash="dash"),
            ))
            fig.update_layout(title="ROC Curve", xaxis_title="False Positive Rate",
                              yaxis_title="True Positive Rate")
            st.plotly_chart(style_fig(fig, height=340), use_container_width=True)

        with right:
            # Confusion matrix heatmap
            cm = result["confusion_matrix"]
            fig = px.imshow(
                cm, text_auto=True, color_continuous_scale=["#1C2440", stl.ACCENT, stl.ACCENT_3],
                labels=dict(x="Predicted", y="Actual", color="Count"),
                x=["Not Churned", "Churned"], y=["Not Churned", "Churned"],
            )
            fig.update_layout(title="Confusion Matrix")
            st.plotly_chart(style_fig(fig, height=340), use_container_width=True)

        # Feature importance
        imp = result["importances"]
        imp_df = imp.reset_index()
        imp_df.columns = ["Feature", "Importance"]
        fig = px.bar(imp_df, x="Importance", y="Feature", orientation="h",
                     title="Churn Feature Importance",
                     color_discrete_sequence=[stl.ACCENT_4])
        fig.update_layout(showlegend=False)
        st.plotly_chart(style_fig(fig, height=380), use_container_width=True)

        # At-risk customer predictions
        st.markdown("### 🎯 Customer Risk Scoring")
        with st.spinner("Scoring customers..."):
            preds = an.predict_churn(result["model"], result["encoders"], churn_train)
        churn_scored = churn_train.reset_index(drop=True).copy()
        churn_scored["churn_probability"] = preds["churn_probability"]
        churn_scored["risk_label"] = np.where(
            churn_scored["churn_probability"] >= 0.7, "🔴 High",
            np.where(churn_scored["churn_probability"] >= 0.4, "🟠 Medium", "🟢 Low"),
        )
        at_risk = churn_scored.sort_values("churn_probability", ascending=False).head(20)
        show_cols = [c for c in ["Customer_Id", "Country", "Industry", "Segment",
                                 "total_paid", "n_tickets", "churn_probability", "risk_label"]
                     if c in at_risk.columns]
        st.dataframe(
            at_risk[show_cols].style.format({"churn_probability": "{:.0%}",
                                             "total_paid": "${:,.0f}"}),
            use_container_width=True,
            hide_index=True,
        )

    # ---------- Revenue forecast ----------
    st.markdown("### 💰 Revenue Forecast")
    months_ahead = st.slider("Forecast horizon (months)", 1, 6, 4)
    fc = an.forecast_revenue(revenue_f, months_ahead=months_ahead)
    if fc.empty:
        st.info("Not enough revenue data to forecast with the current filters.")
    else:
        actual = fc[fc["type"] == "Actual"]
        forecast = fc[fc["type"] == "Forecast"]
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=actual["period"], y=actual["revenue"], mode="lines+markers",
            name="Actual", line=dict(color=stl.ACCENT_2, width=2.5),
        ))
        fig.add_trace(go.Scatter(
            x=forecast["period"], y=forecast["forecast"], mode="lines+markers",
            name="Forecast", line=dict(color=stl.ACCENT, width=2.5, dash="dot"),
        ))
        fig.update_layout(title=f"Monthly Revenue Forecast ({months_ahead} months ahead)",
                          xaxis_title="Period", yaxis_title="Revenue ($)")
        st.plotly_chart(style_fig(fig, height=340), use_container_width=True)

# ===========================================================================
# PAGE 5 - EXPORT & REPORT
# ===========================================================================
elif page == "📤 Export & Report":
    st.markdown(
        f'<div class="dashboard-title">📤 Export & Reporting</div>'
        f'<div class="dashboard-subtitle">Download the filtered datasets or a branded '
        f'executive summary report</div>',
        unsafe_allow_html=True,
    )

    st.markdown("### 📄 Export the Filtered Datasets")
    st.caption("All exports respect the global filters selected in the sidebar.")

    c1, c2, c3, c4 = st.columns(4)
    exports = {
        "Subscriptions/Plans": subs_f,
        "Revenue/Payments": revenue_f,
        "Usage Events": usage_f,
        "Support Tickets": support_f,
    }
    for col, (name, df) in zip([c1, c2, c3, c4], exports.items()):
        with col:
            st.download_button(
                label=f"⬇️ {name} (CSV)",
                data=rep.to_csv_bytes(df),
                file_name=f"{name.lower().replace('/', '_').replace(' ', '_')}.csv",
                mime="text/csv",
                use_container_width=True,
            )

    st.markdown("### 📊 Download Combined Excel Workbook")
    excel_bytes = rep.to_excel_bytes({
        "Subscriptions": subs_f,
        "Revenue": revenue_f,
        "Usage": usage_f,
        "Support": support_f,
    })
    st.download_button(
        label="⬇️ All Datasets (Excel)",
        data=excel_bytes,
        file_name="saas_business_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    st.markdown("### 🧾 Executive Summary Report (PDF)")
    st.caption("Generate a branded one-page PDF summarizing current KPIs.")
    kpis_pdf = {
        "Total Customers": f"{an.total_customers(subs_f):,}",
        "Total Revenue": f"${an.total_revenue(revenue_f):,.0f}",
        "Active Subscriptions": f"{an.active_customers(subs_f):,}",
        "Churn Rate": f"{an.churn_rate(subs_f):.1f}%",
        "Retention Rate": f"{an.retention_rate(subs_f):.1f}%",
        "Support Tickets": f"{an.total_tickets(support_f):,}",
        "Avg Session (min)": f"{an.avg_session_minutes(usage_f):,.0f}",
        "Avg Subscription Days": f"{an.avg_subscription_duration(subs_f):,.0f}",
    }
    generated = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    pdf_bytes = rep.build_pdf_exec_summary(kpis_pdf, generated)
    st.download_button(
        label="⬇️ Download Executive Report (PDF)",
        data=pdf_bytes,
        file_name="saas_executive_report.pdf",
        mime="application/pdf",
        use_container_width=True,
    )

    st.markdown("---")
    st.markdown(
        f'<div class="footer-note">Generated {generated} · Filters: '
        f'{", ".join(filter_countries) if filter_countries else "All"} / '
        f'{", ".join(filter_plans)}</div>',
        unsafe_allow_html=True,
    )
