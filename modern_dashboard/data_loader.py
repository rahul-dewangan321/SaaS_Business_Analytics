"""
data_loader.py
-------------
Core data loading, cleaning and transformation layer for the
modernized End-to-End SaaS Business Analytics dashboard.

Loads the six business datasets, merges them into analysis-ready
DataFrames and exposes cache-friendly accessors for the dashboard.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent / "Dataset" / "Cleaned Dataset"

FILES = {
    "customers": "customers_clean.csv",
    "plans": "plans_clean.csv",
    "subscriptions": "subscriptions_clean.csv",
    "payments": "payments_clean.csv",
    "usage": "usage_clean.csv",
    "support": "support_clean.csv",
}

# Normalise lookup-style categorical fields ("Unknown" -> NA) so that
# downstream groupings behave consistently.
NORMALISE_CATEGORIES = {
    "customers": ["Country", "Industry"],
    "usage": ["Feature_Name"],
}


def _read(name: str) -> pd.DataFrame:
    """Read a single cleaned CSV."""
    path = BASE_DIR / FILES[name]
    return pd.read_csv(path)


def _normalise(df: pd.DataFrame, cols) -> pd.DataFrame:
    for col in cols:
        if col in df.columns:
            df[col] = df[col].replace({"Unknown": pd.NA, "unknown": pd.NA, "": pd.NA})
    return df


@st.cache_data(show_spinner="Loading datasets...")
def load_all() -> dict[str, pd.DataFrame]:
    """Load and return every raw business table keyed by name."""
    data = {name: _read(name) for name in FILES}
    for name, cols in NORMALISE_CATEGORIES.items():
        data[name] = _normalise(data[name], cols)
    return data


@st.cache_data(show_spinner="Building merged analysis data...")
def build_customer_subscription() -> pd.DataFrame:
    """Customers joined with their (latest) subscription and plan."""
    data = load_all()
    cust = data["customers"]
    subs = data["subscriptions"].copy()
    plans = data["plans"]

    subs["Start_Date"] = pd.to_datetime(subs["Start_Date"])
    subs["End_Date"] = pd.to_datetime(subs["End_Date"], errors="coerce")

    merged = subs.merge(plans, on="Plan_Id", how="left")
    merged = merged.merge(cust, on="Customer_Id", how="left")

    # Latest subscription per customer
    latest = (
        merged.sort_values("Start_Date")
        .groupby("Customer_Id", as_index=False)
        .tail(1)
    )
    latest["Payment_Version"] = 0  # placeholder used by insights
    return latest


@st.cache_data(show_spinner="Building revenue data...")
def build_revenue() -> pd.DataFrame:
    """Payments joined with subscription/plan/customer dimensions."""
    data = load_all()
    pay = data["payments"].copy()
    subs = data["subscriptions"]
    plans = data["plans"]
    cust = data["customers"]

    pay["Payment_Date"] = pd.to_datetime(pay["Payment_Date"])
    pay["YearMonth"] = pay["Payment_Date"].dt.to_period("M")

    df = pay.merge(subs, on="Subscription_Id", how="left")
    df = df.merge(plans, on="Plan_Id", how="left")
    df = df.merge(cust, on="Customer_Id", how="left")
    return df


@st.cache_data(show_spinner="Building usage data...")
def build_usage() -> pd.DataFrame:
    """Usage events joined with customer dimensions."""
    data = load_all()
    usage = data["usage"].copy()
    cust = data["customers"]

    usage["Event_Date"] = pd.to_datetime(usage["Event_Date"])
    usage["YearMonth"] = usage["Event_Date"].dt.to_period("M")

    df = usage.merge(cust, on="Customer_Id", how="left")
    return df


@st.cache_data(show_spinner="Building support data...")
def build_support() -> pd.DataFrame:
    """Support tickets joined with customer dimensions."""
    data = load_all()
    support = data["support"].copy()
    cust = data["customers"]

    support["Ticket_Date"] = pd.to_datetime(support["Ticket_Date"])
    support["YearMonth"] = support["Ticket_Date"].dt.to_period("M")

    df = support.merge(cust, on="Customer_Id", how="left")
    return df


@st.cache_data(show_spinner="Building churn dataset...")
def build_churn_dataset() -> pd.DataFrame:
    """
    Feature-engineered, customer-level dataset used for predictive churn
    modelling. One row per customer with behavioural + demographic features.
    """
    data = load_all()
    cust = data["customers"].copy()
    subs = data["subscriptions"].copy()
    pay = data["payments"].copy()
    usage = data["usage"].copy()
    support = data["support"].copy()

    # Subscription-level features
    subs["Start_Date"] = pd.to_datetime(subs["Start_Date"])
    subs["End_Date"] = pd.to_datetime(subs["End_Date"], errors="coerce")
    subs_agg = (
        subs.groupby("Customer_Id")
        .agg(
            n_subscriptions=("Subscription_Id", "count"),
            avg_subscription_days=("Subscription_Days", "mean"),
            max_end_date=("End_Date", "max"),
        )
        .reset_index()
    )

    # Target: churned if latest subscription status is Churned/Cancelled
    status_map = {"Active": 0, "Churned": 1, "Cancelled": 1}
    latest_status = (
        subs.sort_values("Start_Date")
        .groupby("Customer_Id")["Status"]
        .last()
        .map(status_map)
        .fillna(0)
        .astype(int)
    )
    subs_agg["is_churned"] = subs_agg["Customer_Id"].map(latest_status)

    # Payment-level features (attach Customer_Id via subscription link)
    pay["Payment_Date"] = pd.to_datetime(pay["Payment_Date"])
    pay = pay.merge(subs[["Subscription_Id", "Customer_Id"]], on="Subscription_Id", how="left")
    pay_good = pay[pay["Payment_Status"] == "Paid"]
    pay_agg = (
        pay_good.groupby("Customer_Id")
        .agg(
            total_paid=("Amount", "sum"),
            n_payments=("Payment_Id", "count"),
            avg_amount=("Amount", "mean"),
        )
        .reset_index()
    )

    # Usage-level features
    usage["Event_Date"] = pd.to_datetime(usage["Event_Date"])
    usage_agg = (
        usage.groupby("Customer_Id")
        .agg(
            total_logins=("Login_Count", "sum"),
            total_session_minutes=("Session_Minutes", "sum"),
            n_active_days=("Event_Date", "nunique"),
            n_used_features=("Feature_Name", "nunique"),
        )
        .reset_index()
    )

    # Support-level features (proxy for friction)
    support["Ticket_Date"] = pd.to_datetime(support["Ticket_Date"])
    support_agg = (
        support.groupby("Customer_Id")
        .agg(
            n_tickets=("Ticket_Id", "count"),
            avg_resolution_time=("Resolution_Time", "mean"),
        )
        .reset_index()
    )

    df = cust.merge(subs_agg, on="Customer_Id", how="left")
    df = df.merge(pay_agg, on="Customer_Id", how="left")
    df = df.merge(usage_agg, on="Customer_Id", how="left")
    df = df.merge(support_agg, on="Customer_Id", how="left")

    # Fill missing behaviour with 0 (customer never paid / used / opened ticket)
    for col in [
        "n_subscriptions", "avg_subscription_days", "total_paid",
        "n_payments", "avg_amount", "total_logins",
        "total_session_minutes", "n_active_days", "n_used_features",
        "n_tickets", "avg_resolution_time",
    ]:
        df[col] = df[col].fillna(0)

    df["is_churned"] = df["is_churned"].fillna(0).astype(int)

    return df
