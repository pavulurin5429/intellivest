"""
Train HMM regime model (on SPY price history) and credit scorecard
(on synthetic-but-realistic financial features with domain-rule labels).
Run from project root: python -m backend.ml.train_models
"""
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import numpy as np
import pandas as pd
import yfinance as yf
from loguru import logger

from backend.ml.hmm_regime import train_hmm
from backend.ml.credit_scorecard import train


# ─── 1. HMM Regime Model ────────────────────────────────────────────────────

def train_hmm_on_spy():
    logger.info("Downloading SPY 10-year price history for HMM training...")
    spy = yf.Ticker("SPY")
    hist = spy.history(period="10y")

    if hist.empty:
        logger.error("Could not fetch SPY data. Check yfinance.")
        return

    logger.info(f"SPY data: {len(hist)} trading days ({hist.index[0].date()} to {hist.index[-1].date()})")

    stats = train_hmm(hist, n_states=3, save=True)
    logger.success(
        f"HMM trained. Log-likelihood: {stats['log_likelihood']}, "
        f"regime distribution: {stats['regime_counts']}"
    )


# ─── 2. Credit Scorecard ────────────────────────────────────────────────────
# Feature names MUST match exactly what feature_engineering.py produces.

_SAFE_PROFILE = {
    # Liquidity
    "current_ratio":          (2.0, 0.4, "lognormal"),
    "quick_ratio":            (1.4, 0.4, "lognormal"),
    "cash_ratio":             (0.6, 0.4, "lognormal"),
    "operating_cash_ratio":   (0.5, 0.3, "lognormal"),
    "working_capital_ratio":  (0.20, 0.08, "normal"),
    # Leverage
    "debt_to_equity":         (0.5, 0.5, "lognormal"),
    "debt_to_assets":         (0.25, 0.12, "normal"),
    "equity_multiplier":      (2.0, 0.4, "lognormal"),
    "interest_coverage":      (8.0, 0.5, "lognormal"),
    "debt_service_coverage":  (0.35, 0.2, "normal"),
    "long_term_debt_ratio":   (0.15, 0.08, "normal"),
    "total_liab_to_equity":   (0.7, 0.4, "lognormal"),
    # Profitability
    "gross_margin":           (0.50, 0.12, "normal"),
    "operating_margin":       (0.18, 0.06, "normal"),
    "net_profit_margin":      (0.12, 0.05, "normal"),
    "return_on_assets":       (0.10, 0.04, "normal"),
    "return_on_equity":       (0.18, 0.06, "normal"),
    "ebitda_margin":          (0.22, 0.06, "normal"),
    "asset_turnover":         (0.8, 0.3, "lognormal"),
    "equity_turnover":        (2.0, 0.5, "lognormal"),
    # Cash Flow
    "operating_cf_margin":    (0.15, 0.05, "normal"),
    "free_cf_margin":         (0.10, 0.04, "normal"),
    "capex_ratio":            (0.05, 0.02, "normal"),
    "cf_to_debt":             (0.35, 0.15, "normal"),
    "cf_to_assets":           (0.10, 0.04, "normal"),
    # Efficiency
    "inventory_turnover":     (6.0, 0.5, "lognormal"),
    "receivables_turnover":   (8.0, 0.4, "lognormal"),
    "payables_turnover":      (7.0, 0.4, "lognormal"),
    "days_sales_outstanding": (45.0, 10.0, "normal"),
    "days_inventory_outstanding": (60.0, 15.0, "normal"),
    # Growth
    "revenue_yoy_growth":     (0.10, 0.06, "normal"),
    "earnings_yoy_growth":    (0.12, 0.08, "normal"),
    "revenue_qoq_growth":     (0.03, 0.03, "normal"),
    "operating_cf_growth":    (0.10, 0.08, "normal"),
    # Market
    "pe_ratio":               (20.0, 0.4, "lognormal"),
    "pb_ratio":               (3.0, 0.5, "lognormal"),
    "ps_ratio":               (3.0, 0.5, "lognormal"),
    "dividend_yield":         (0.02, 0.01, "normal"),
    "beta":                   (0.9, 0.3, "normal"),
    # Volatility
    "volatility_30d":         (0.20, 0.05, "normal"),
    "volatility_90d":         (0.18, 0.04, "normal"),
    "price_momentum_90d":     (0.08, 0.10, "normal"),
}

_RISKY_PROFILE = {
    "current_ratio":          (0.8, 0.4, "lognormal"),
    "quick_ratio":            (0.5, 0.4, "lognormal"),
    "cash_ratio":             (0.05, 0.04, "normal"),
    "operating_cash_ratio":   (0.1, 0.15, "normal"),
    "working_capital_ratio":  (-0.10, 0.12, "normal"),
    "debt_to_equity":         (3.0, 0.7, "lognormal"),
    "debt_to_assets":         (0.70, 0.12, "normal"),
    "equity_multiplier":      (5.0, 0.6, "lognormal"),
    "interest_coverage":      (1.0, 0.8, "normal"),
    "debt_service_coverage":  (0.05, 0.10, "normal"),
    "long_term_debt_ratio":   (0.45, 0.12, "normal"),
    "total_liab_to_equity":   (4.0, 0.8, "lognormal"),
    "gross_margin":           (0.15, 0.10, "normal"),
    "operating_margin":       (-0.05, 0.10, "normal"),
    "net_profit_margin":      (-0.08, 0.10, "normal"),
    "return_on_assets":       (-0.04, 0.06, "normal"),
    "return_on_equity":       (-0.10, 0.12, "normal"),
    "ebitda_margin":          (0.04, 0.08, "normal"),
    "asset_turnover":         (0.4, 0.3, "lognormal"),
    "equity_turnover":        (0.8, 0.5, "lognormal"),
    "operating_cf_margin":    (-0.02, 0.08, "normal"),
    "free_cf_margin":         (-0.06, 0.08, "normal"),
    "capex_ratio":            (0.15, 0.06, "normal"),
    "cf_to_debt":             (0.03, 0.08, "normal"),
    "cf_to_assets":           (-0.01, 0.05, "normal"),
    "inventory_turnover":     (2.5, 0.5, "lognormal"),
    "receivables_turnover":   (4.0, 0.5, "lognormal"),
    "payables_turnover":      (5.0, 0.5, "lognormal"),
    "days_sales_outstanding": (90.0, 20.0, "normal"),
    "days_inventory_outstanding": (140.0, 30.0, "normal"),
    "revenue_yoy_growth":     (-0.10, 0.08, "normal"),
    "earnings_yoy_growth":    (-0.20, 0.12, "normal"),
    "revenue_qoq_growth":     (-0.03, 0.04, "normal"),
    "operating_cf_growth":    (-0.15, 0.12, "normal"),
    "pe_ratio":               (50.0, 0.7, "lognormal"),
    "pb_ratio":               (6.0, 0.8, "lognormal"),
    "ps_ratio":               (6.0, 0.8, "lognormal"),
    "dividend_yield":         (0.0, 0.01, "normal"),
    "beta":                   (1.8, 0.4, "normal"),
    "volatility_30d":         (0.45, 0.10, "normal"),
    "volatility_90d":         (0.40, 0.08, "normal"),
    "price_momentum_90d":     (-0.15, 0.12, "normal"),
}


def _sample_features(profile: dict, n: int, rng: np.random.Generator) -> pd.DataFrame:
    rows = {}
    for feat, (loc, scale, dist) in profile.items():
        if dist == "lognormal":
            rows[feat] = rng.lognormal(np.log(max(loc, 1e-6)), scale, n)
        else:
            rows[feat] = rng.normal(loc, scale, n)
    return pd.DataFrame(rows)


def _generate_credit_dataset(n_samples: int = 6000, seed: int = 42) -> tuple[pd.DataFrame, pd.Series]:
    rng = np.random.default_rng(seed)
    n_safe  = int(n_samples * 0.65)
    n_risky = n_samples - n_safe

    df_safe  = _sample_features(_SAFE_PROFILE,  n_safe,  rng)
    df_risky = _sample_features(_RISKY_PROFILE, n_risky, rng)

    X = pd.concat([df_safe, df_risky], ignore_index=True)
    y = pd.Series([0] * n_safe + [1] * n_risky, name="default")

    # Clip extreme values
    X = X.clip(lower=-100, upper=1000)

    idx = rng.permutation(len(X))
    return X.iloc[idx].reset_index(drop=True), y.iloc[idx].reset_index(drop=True)


def train_credit_scorecard():
    logger.info("Generating synthetic credit dataset (6,000 samples, 42 features)...")
    X, y = _generate_credit_dataset(n_samples=6000)
    logger.info(f"Dataset: {len(X)} rows x {X.shape[1]} features, default rate={y.mean():.1%}")

    metrics = train(X, y, save=True)
    logger.success(
        f"Credit scorecard trained. "
        f"XGB AUC={metrics['xgb_cv_auc']:.4f} (Gini={metrics['xgb_cv_gini']:.4f}), "
        f"LR AUC={metrics['lr_cv_auc']:.4f} (Gini={metrics['lr_cv_gini']:.4f})"
    )


# ─── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print(" IntelliVest — Model Training")
    print("=" * 60)

    print("\n[1/2] Training HMM Market Regime Model on SPY...")
    train_hmm_on_spy()

    print("\n[2/2] Training Credit Scorecard (XGBoost + LR ensemble, 42 features)...")
    train_credit_scorecard()

    print("\nAll models saved to backend/ml/models/")
    print("Restart the backend server to load new models.")
