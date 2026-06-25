"""
Hidden Markov Model for market regime detection.
3 states: Bull (0), Sideways (1), Bear (2).
Trained on daily returns and volatility features.
"""

import numpy as np
import pandas as pd
import joblib
import os
from typing import Optional
from hmmlearn import hmm
from loguru import logger


MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "hmm_regime.joblib")

_model: Optional[hmm.GaussianHMM] = None

REGIME_LABELS = {0: "BULL", 1: "SIDEWAYS", 2: "BEAR"}


def build_hmm_features(price_df: pd.DataFrame, window: int = 20) -> np.ndarray:
    """
    Build feature matrix for HMM from price history.
    Features: daily return, rolling volatility, rolling momentum.
    """
    df = price_df.copy()
    df["return"] = df["Close"].pct_change()
    df["volatility"] = df["return"].rolling(window).std()
    df["momentum"] = df["Close"].pct_change(window)
    df = df.dropna()
    return df[["return", "volatility", "momentum"]].values


def train_hmm(price_df: pd.DataFrame, n_states: int = 3, save: bool = True) -> dict:
    """Train HMM on price history DataFrame. Returns regime sequence and model stats."""
    X = build_hmm_features(price_df)
    lengths = [len(X)]

    model = hmm.GaussianHMM(
        n_components=n_states,
        covariance_type="full",
        n_iter=200,
        random_state=42,
    )
    model.fit(X, lengths)

    if save:
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        joblib.dump(model, MODEL_PATH)
        logger.info("Saved HMM regime model.")

    global _model
    _model = model

    regimes = model.predict(X)
    regime_counts = {REGIME_LABELS[i]: int((regimes == i).sum()) for i in range(n_states)}

    logger.info(f"HMM trained. Regime distribution: {regime_counts}")
    return {
        "log_likelihood": round(model.score(X), 2),
        "regime_counts": regime_counts,
        "n_states": n_states,
    }


def load_hmm():
    global _model
    if _model is None and os.path.exists(MODEL_PATH):
        _model = joblib.load(MODEL_PATH)
        logger.info("Loaded HMM regime model from disk.")


def predict_current_regime(price_df: pd.DataFrame) -> dict:
    """Predict the current market regime from recent price data."""
    load_hmm()
    if _model is None:
        return {"error": "HMM model not trained yet", "regime": "UNKNOWN"}

    X = build_hmm_features(price_df)
    if len(X) == 0:
        return {"error": "Insufficient price data", "regime": "UNKNOWN"}

    regimes = _model.predict(X)
    current_regime_id = int(regimes[-1])
    current_regime = REGIME_LABELS.get(current_regime_id, "UNKNOWN")

    # Recent regime distribution (last 30 days)
    recent = regimes[-30:] if len(regimes) >= 30 else regimes
    recent_dist = {REGIME_LABELS[i]: round(float((recent == i).sum() / len(recent)), 3) for i in range(3)}

    # State transition probabilities for current state
    transition_probs = {
        REGIME_LABELS[i]: round(float(_model.transmat_[current_regime_id][i]), 3)
        for i in range(3)
    }

    return {
        "current_regime": current_regime,
        "regime_id": current_regime_id,
        "recent_distribution_30d": recent_dist,
        "transition_probabilities": transition_probs,
    }


def get_regime_series(price_df: pd.DataFrame) -> pd.Series:
    """Return full regime label series aligned to price_df index (after warmup)."""
    load_hmm()
    if _model is None:
        return pd.Series(dtype=str)

    X = build_hmm_features(price_df)
    regimes = _model.predict(X)
    regime_labels = [REGIME_LABELS[r] for r in regimes]

    # Align to trimmed index (dropna removes first `window` rows)
    trimmed_index = price_df.dropna().index[-len(X):]
    return pd.Series(regime_labels, index=trimmed_index, name="regime")
