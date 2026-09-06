"""
analytics.py
------------
Analytics + predictive modelling layer.

Implements:
  * KPI computations across the business dimensions
  * Customer churn prediction (Gradient Boosting classifier)
  * Revenue forecasting (Holt-Winters style / exponential smoothing)
  * Feature-importance explanation for the churn model
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score, roc_curve, confusion_matrix

DARK_COLORS = ["#7C5CFF", "#00C2FF", "#FF6B9D", "#FFC24B", "#34D399", "#F97316"]


# Small helper so the churn model can be cached inside Streamlit without
# importing streamlit at module import time (keeps unit-testing easy).
def st_cache_safe(func):
    try:
        import streamlit as st

        return st.cache_resource(func)
    except Exception:
        return func


# ---------------------------------------------------------------------------
# KPI helpers
# ---------------------------------------------------------------------------
def total_customers(subs: pd.DataFrame) -> int:
    return int(subs["Customer_Id"].nunique())


def active_customers(subs: pd.DataFrame) -> int:
    return int((subs["Status"] == "Active").sum())


def churned_customers(subs: pd.DataFrame) -> int:
    return int(subs["Status"].isin(["Churned", "Cancelled"]).sum())


def churn_rate(subs: pd.DataFrame) -> float:
    n = len(subs)
    if n == 0:
        return 0.0
    return float(subs["Status"].isin(["Churned", "Cancelled"]).sum() / n * 100)


def total_revenue(pay: pd.DataFrame) -> float:
    return float(pay.loc[pay["Payment_Status"] == "Paid", "Amount"].sum())


def avg_session_minutes(usage: pd.DataFrame) -> float:
    return float(usage["Session_Minutes"].mean()) if len(usage) else 0.0


def total_tickets(support: pd.DataFrame) -> int:
    return int(len(support))


def retention_rate(subs: pd.DataFrame) -> float:
    n = len(subs)
    if n == 0:
        return 0.0
    return float((subs["Status"] == "Active").sum() / n * 100)


def avg_subscription_duration(subs: pd.DataFrame) -> float:
    return float(subs["Subscription_Days"].mean()) if len(subs) else 0.0


# ---------------------------------------------------------------------------
# Churn prediction
# ---------------------------------------------------------------------------
# NOTE: `avg_subscription_days` is omitted on purpose - it is a direct
# consequence of churn (leaked target) and would give a perfectly (and
# misleadingly) accurate model. We keep behaviour that precedes churn.
FEATURE_COLS = [
    "n_subscriptions", "total_paid",
    "n_payments", "avg_amount", "total_logins",
    "total_session_minutes", "n_active_days", "n_used_features",
    "n_tickets", "avg_resolution_time",
]

CATEGORICAL_COLS = ["Country", "Industry", "Segment", "Company_Size"]


def _encode_categoricals(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    encoders: dict[str, LabelEncoder] = {}
    out = df.copy()
    for col in CATEGORICAL_COLS:
        if col in out.columns:
            le = LabelEncoder()
            filled = out[col].astype(str).fillna("Unknown")
            out[col] = le.fit_transform(filled)
            encoders[col] = le
    return out, encoders


@st_cache_safe
def train_churn_model(
    data: pd.DataFrame,
) -> dict:
    """
    Train a Gradient Boosting classifier to predict customer churn.
    Splits the data, fits the model and returns model + evaluation metrics.
    """
    df, encoders = _encode_categoricals(data.copy())
    X = df[FEATURE_COLS + CATEGORICAL_COLS].astype(float)
    y = df["is_churned"].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    model = GradientBoostingClassifier(
        n_estimators=120, max_depth=3, learning_rate=0.1, random_state=42
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    acc = accuracy_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_proba)
    fpr, tpr, _ = roc_curve(y_test, y_proba)
    cm = confusion_matrix(y_test, y_pred)

    importances = pd.Series(model.feature_importances_, index=X.columns)
    importances = importances.sort_values(ascending=True)

    return {
        "model": model,
        "encoders": encoders,
        "accuracy": acc,
        "auc": auc,
        "fpr": fpr,
        "tpr": tpr,
        "confusion_matrix": cm,
        "importances": importances,
        "n_train": len(X_train),
        "n_test": len(X_test),
        "churned_rate": float(y.mean() * 100),
    }


def predict_churn(model, encoders, features: pd.DataFrame) -> pd.DataFrame:
    """Apply the trained model to a feature table and return scores."""
    df = features.copy()
    for col, le in encoders.items():
        if col in df.columns:
            filled = df[col].astype(str).fillna("Unknown")
            df[col] = le.transform(filled)

    X = df[FEATURE_COLS + CATEGORICAL_COLS].astype(float)
    proba = model.predict_proba(X)[:, 1]
    label = (proba >= 0.5).astype(int)
    return pd.DataFrame({"churn_probability": proba, "predicted_churn": label})


# ---------------------------------------------------------------------------
# Revenue forecasting
# ---------------------------------------------------------------------------
def forecast_revenue(
    pay: pd.DataFrame,
    months_ahead: int = 4,
) -> pd.DataFrame:
    """
    Monthly revenue forecast using simple exponential smoothing /
    Holt's linear trend, based on actual paid revenue.
    """
    rev = (
        pay[pay["Payment_Status"] == "Paid"]
        .groupby(pay["Payment_Date"].dt.to_period("M"))
        .agg(revenue=("Amount", "sum"))
        .sort_index()
    )
    if len(rev) < 2:
        return pd.DataFrame()

    values = rev["revenue"].astype(float).values
    idx = rev.index.astype(str).tolist()

    # simple exponential smoothing forecast
    alpha = 0.4
    level = values[0]
    for v in values[1:]:
        level = alpha * v + (1 - alpha) * level
    base = float(level)

    # approximate monthly trend from first/last actual
    trend = 0.0
    if len(values) >= 3:
        trend = (values[-1] - values[0]) / max(len(values) - 1, 1)

    last_period = rev.index.astype(object)
    forecast_rows = []
    horizon = last_period[-1] + 1
    for _ in range(months_ahead):
        row = {
            "period": str(horizon),
            "revenue": None,
            "forecast": base,
            "type": "Forecast",
        }
        forecast_rows.append(row)
        forecast_rows[-1]["forecast"] = max(base, 0)
        base = base + trend
        horizon += 1

    actual_rows = [
        {"period": str(p), "revenue": float(r), "forecast": None, "type": "Actual"}
        for p, r in zip(idx, values)
    ]

    combined = pd.DataFrame(actual_rows + forecast_rows)
    return combined
