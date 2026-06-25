"""
Simple backtesting engine.
Simulates a strategy over 3 years of price data and computes Sharpe ratio,
max drawdown, and other performance metrics. No lookahead bias.
"""

import numpy as np
import pandas as pd
from loguru import logger


def run_backtest(
    price_df: pd.DataFrame,
    signals: pd.Series,
    initial_capital: float = 100_000,
    transaction_cost: float = 0.001,
) -> dict:
    """
    Backtest a signal series against price history.

    signals: pd.Series of {1: long, -1: short, 0: flat} aligned to price_df index.
    transaction_cost: fraction of trade value charged per trade (e.g. 0.001 = 0.1%).
    Returns performance metrics dict.
    """
    df = price_df[["Close"]].copy()
    df["signal"] = signals.reindex(df.index).fillna(0).shift(1)  # shift to avoid lookahead
    df["returns"] = df["Close"].pct_change()
    df["strategy_returns"] = df["signal"] * df["returns"]

    # Deduct transaction costs on signal changes
    signal_changes = df["signal"].diff().abs() > 0
    df.loc[signal_changes, "strategy_returns"] -= transaction_cost

    df["cumulative_returns"] = (1 + df["strategy_returns"]).cumprod()
    df["portfolio_value"] = initial_capital * df["cumulative_returns"]

    # Metrics
    strategy_rets = df["strategy_returns"].dropna()
    total_return = float(df["cumulative_returns"].iloc[-1] - 1)
    annual_return = float((1 + total_return) ** (252 / len(strategy_rets)) - 1)
    annual_vol = float(strategy_rets.std() * np.sqrt(252))
    sharpe = round(annual_return / annual_vol, 4) if annual_vol > 0 else 0

    rolling_max = df["cumulative_returns"].cummax()
    drawdowns = (df["cumulative_returns"] - rolling_max) / rolling_max
    max_drawdown = float(drawdowns.min())

    buy_hold_return = float(df["Close"].iloc[-1] / df["Close"].iloc[0] - 1)
    n_trades = int(signal_changes.sum())

    metrics = {
        "total_return": round(total_return, 4),
        "annual_return": round(annual_return, 4),
        "annual_volatility": round(annual_vol, 4),
        "sharpe_ratio": sharpe,
        "max_drawdown": round(max_drawdown, 4),
        "buy_hold_return": round(buy_hold_return, 4),
        "n_trades": n_trades,
        "final_portfolio_value": round(float(df["portfolio_value"].iloc[-1]), 2),
        "start_date": str(df.index[0].date()),
        "end_date": str(df.index[-1].date()),
    }

    logger.info(f"Backtest complete: Sharpe={sharpe:.2f}, Total Return={total_return:.1%}, Max DD={max_drawdown:.1%}")
    return metrics, df


def momentum_signal(price_df: pd.DataFrame, short_window: int = 20, long_window: int = 60) -> pd.Series:
    """
    Simple moving average crossover signal as a baseline strategy.
    Returns 1 when short MA > long MA, -1 otherwise.
    """
    short_ma = price_df["Close"].rolling(short_window).mean()
    long_ma = price_df["Close"].rolling(long_window).mean()
    signal = (short_ma > long_ma).astype(int).replace(0, -1)
    signal[:long_window] = 0  # no signal during warmup
    return signal


if __name__ == "__main__":
    import yfinance as yf
    df = yf.Ticker("SPY").history(period="3y")
    signals = momentum_signal(df)
    metrics, result_df = run_backtest(df, signals)
    print(metrics)
