"""
Credit risk scorecard.
XGBoost + Logistic Regression ensemble trained on 42 financial features.
Outputs a credit score (0-100) and a Gini coefficient for model validation.
"""

from __future__ import annotations
import numpy as np
import pandas as pd
import joblib
import os
from typing import Optional
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.metrics import roc_auc_score
from xgboost import XGBClassifier
from loguru import logger


MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
os.makedirs(MODEL_DIR, exist_ok=True)

XGB_PATH     = os.path.join(MODEL_DIR, "xgb_credit.joblib")
LR_PATH      = os.path.join(MODEL_DIR, "lr_credit.joblib")
COLUMNS_PATH = os.path.join(MODEL_DIR, "credit_feature_columns.joblib")

_xgb: Optional[XGBClassifier] = None
_lr_pipeline: Optional[Pipeline] = None
_feature_columns: Optional[list] = None


def gini_coefficient(y_true: np.ndarray, y_pred_proba: np.ndarray) -> float:
    """Gini = 2 * AUC - 1. Industry standard credit model metric."""
    auc = roc_auc_score(y_true, y_pred_proba)
    return round(2 * auc - 1, 4)


def train(X: pd.DataFrame, y: pd.Series, save: bool = True) -> dict:
    """
    Train XGBoost + Logistic Regression ensemble on labeled credit data.
    y: binary (1 = default/high-risk, 0 = safe)
    Returns training metrics including Gini on hold-out CV folds.
    """
    X_filled = X.fillna(X.median(numeric_only=True))

    xgb = XGBClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="auc",
        random_state=42,
        n_jobs=-1,
    )

    lr_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("lr", LogisticRegression(max_iter=1000, C=0.1, random_state=42)),
    ])

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    xgb_aucs = cross_val_score(xgb, X_filled, y, cv=cv, scoring="roc_auc")
    lr_aucs  = cross_val_score(lr_pipeline, X_filled, y, cv=cv, scoring="roc_auc")

    xgb.fit(X_filled, y)
    lr_pipeline.fit(X_filled, y)

    if save:
        joblib.dump(xgb, XGB_PATH)
        joblib.dump(lr_pipeline, LR_PATH)
        joblib.dump(list(X_filled.columns), COLUMNS_PATH)
        logger.info("Saved credit scorecard models.")

    global _xgb, _lr_pipeline, _feature_columns
    _xgb = xgb
    _lr_pipeline = lr_pipeline
    _feature_columns = list(X_filled.columns)

    metrics = {
        "xgb_cv_auc":  round(xgb_aucs.mean(), 4),
        "xgb_cv_gini": round(2 * xgb_aucs.mean() - 1, 4),
        "lr_cv_auc":   round(lr_aucs.mean(), 4),
        "lr_cv_gini":  round(2 * lr_aucs.mean() - 1, 4),
    }
    logger.info(f"Training metrics: {metrics}")
    return metrics


def load_models():
    global _xgb, _lr_pipeline, _feature_columns
    if _xgb is None and os.path.exists(XGB_PATH):
        _xgb = joblib.load(XGB_PATH)
        _lr_pipeline = joblib.load(LR_PATH)
        if os.path.exists(COLUMNS_PATH):
            _feature_columns = joblib.load(COLUMNS_PATH)
        logger.info("Loaded credit scorecard models from disk.")


def _align_features(df: pd.DataFrame) -> pd.DataFrame:
    """Reorder and fill missing columns to match training feature set."""
    if _feature_columns is None:
        return df
    for col in _feature_columns:
        if col not in df.columns:
            df[col] = np.nan
    # Keep only training columns, in order
    df = df[_feature_columns]
    # Fill any NaN with column medians (use 0 for single-row prediction)
    for col in df.columns:
        if df[col].isna().any():
            df[col] = df[col].fillna(0.0)
    return df


def _risk_label(score: float) -> str:
    if score >= 75:
        return "LOW_RISK"
    elif score >= 50:
        return "MEDIUM_RISK"
    elif score >= 25:
        return "HIGH_RISK"
    return "VERY_HIGH_RISK"


def predict_score(features: "dict | pd.DataFrame") -> dict:
    """
    Predict credit score for a ticker.
    features: dict from extract_features() (single ticker) OR DataFrame (multi-ticker)
    Returns credit score 0-100 (higher = safer) and risk label.
    """
    load_models()
    if _xgb is None:
        return {"error": "Models not trained yet. Run backend/ml/train_models.py first."}

    is_dict = isinstance(features, dict)
    if is_dict:
        ticker = features.pop("ticker", "unknown")
        df = pd.DataFrame([features])
    else:
        ticker = None
        df = features.copy()
        if "ticker" in df.columns:
            df = df.drop(columns=["ticker"])

    df = _align_features(df)

    xgb_proba = _xgb.predict_proba(df)[:, 1]
    lr_proba  = _lr_pipeline.predict_proba(df)[:, 1]

    # Ensemble: 60% XGBoost, 40% Logistic Regression
    ensemble_proba = 0.6 * xgb_proba + 0.4 * lr_proba
    credit_scores  = np.round((1 - ensemble_proba) * 100, 1)

    if is_dict:
        return {
            "ticker":              ticker,
            "credit_score":        float(credit_scores[0]),
            "default_probability": round(float(ensemble_proba[0]), 4),
            "risk_label":          _risk_label(credit_scores[0]),
            "xgb_proba":           round(float(xgb_proba[0]), 4),
            "lr_proba":            round(float(lr_proba[0]), 4),
        }

    return [
        {
            "ticker":              str(df.index[i]) if df.index.dtype != int else f"row_{i}",
            "credit_score":        float(credit_scores[i]),
            "default_probability": round(float(ensemble_proba[i]), 4),
            "risk_label":          _risk_label(credit_scores[i]),
        }
        for i in range(len(df))
    ]
