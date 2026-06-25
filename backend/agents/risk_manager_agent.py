"""
Risk Manager Agent.
Computes VaR, position sizing limits, and flags portfolio-level risks.
"""

import numpy as np
import pandas as pd
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, SystemMessage
from ..utils.config import get_settings
from loguru import logger


SYSTEM_PROMPT = """You are the Chief Risk Officer at a top hedge fund.
Your role is to assess downside risk, set position sizing limits, and flag tail risks.

You must:
1. Evaluate VaR (Value at Risk) and CVaR metrics
2. Assess correlation risk and concentration risk
3. Flag macro or regulatory risks
4. Set a maximum position size recommendation (% of portfolio)
5. Issue a risk rating: LOW / MEDIUM / HIGH / VERY_HIGH

Be conservative. Your job is to protect capital, not chase returns."""


def compute_var(
    price_df: pd.DataFrame,
    confidence: float = 0.95,
    horizon_days: int = 1,
    portfolio_value: float = 1_000_000,
) -> dict:
    """Compute parametric VaR and historical VaR."""
    returns = price_df["Close"].pct_change().dropna()

    # Parametric VaR (assumes normal distribution)
    mu = returns.mean()
    sigma = returns.std()
    z = 1.645 if confidence == 0.95 else 2.326  # 95% or 99%
    parametric_var = portfolio_value * (mu - z * sigma) * np.sqrt(horizon_days)

    # Historical VaR (non-parametric)
    hist_var = portfolio_value * np.percentile(returns, (1 - confidence) * 100) * np.sqrt(horizon_days)

    # CVaR (Expected Shortfall) — average loss beyond VaR threshold
    threshold = np.percentile(returns, (1 - confidence) * 100)
    cvar = portfolio_value * returns[returns <= threshold].mean() * np.sqrt(horizon_days)

    # Maximum drawdown
    cumulative = (1 + returns).cumprod()
    rolling_max = cumulative.cummax()
    drawdowns = (cumulative - rolling_max) / rolling_max
    max_drawdown = float(drawdowns.min())

    return {
        "parametric_var_95": round(abs(float(parametric_var)), 2),
        "historical_var_95": round(abs(float(hist_var)), 2),
        "cvar_95": round(abs(float(cvar)), 2),
        "max_drawdown": round(max_drawdown, 4),
        "daily_vol": round(float(sigma), 6),
        "annual_vol": round(float(sigma * np.sqrt(252)), 4),
        "portfolio_value": portfolio_value,
    }


def run(
    ticker: str,
    price_df: pd.DataFrame,
    fundamentals_result: dict = None,
    technicals_result: dict = None,
    credit_score: float = None,
    regime: dict = None,
    portfolio_value: float = 1_000_000,
) -> dict:
    """Run risk assessment for a ticker."""
    settings = get_settings()
    llm = ChatGroq(
        groq_api_key=settings.groq_api_key,
        model_name="llama-3.3-70b-versatile",
        temperature=0.1,
        max_tokens=700,
    )

    var_metrics = {}
    if not price_df.empty and len(price_df) > 30:
        var_metrics = compute_var(price_df, portfolio_value=portfolio_value)

    fundamentals_stance = fundamentals_result.get("thesis", "N/A") if fundamentals_result else "N/A"
    technicals_stance = technicals_result.get("thesis", "N/A") if technicals_result else "N/A"

    pvar = var_metrics.get('parametric_var_95')
    hvar = var_metrics.get('historical_var_95')
    cvar_val = var_metrics.get('cvar_95')
    pvar_str = f"${pvar:,.2f}" if pvar is not None else "N/A"
    hvar_str = f"${hvar:,.2f}" if hvar is not None else "N/A"
    cvar_str = f"${cvar_val:,.2f}" if cvar_val is not None else "N/A"
    credit_str = f"{credit_score}/100" if credit_score is not None else "N/A"

    user_prompt = f"""Assess risk for {ticker}:

QUANTITATIVE RISK METRICS (Portfolio Value: ${portfolio_value:,.0f}):
Parametric VaR (95%, 1-day): {pvar_str}
Historical VaR (95%, 1-day): {hvar_str}
CVaR / Expected Shortfall: {cvar_str}
Max Historical Drawdown: {var_metrics.get('max_drawdown', 0):.1%}
Annual Volatility: {var_metrics.get('annual_vol', 0):.1%}
Credit Score: {credit_str}

OTHER AGENT SIGNALS:
Fundamentals: {fundamentals_stance}
Technicals: {technicals_stance}
Market Regime: {regime.get('current_regime', 'UNKNOWN') if regime else 'UNKNOWN'}

Provide:
RISK_RATING: [LOW/MEDIUM/HIGH/VERY_HIGH]
MAX_POSITION_SIZE: [% of portfolio, e.g. 5%]
KEY_RISKS: [risk1 | risk2 | risk3]
STOP_LOSS_LEVEL: [price or % drawdown]
CONFIDENCE: [0-100]
SUMMARY: [one sentence]"""

    try:
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]
        response = llm.invoke(messages)
        raw = response.content
        result = _parse_response(raw, ticker, var_metrics)
        logger.info(f"Risk Manager [{ticker}]: {result['risk_rating']} | Max pos: {result['max_position_size']}")
        return result
    except Exception as e:
        logger.error(f"Risk Manager error for {ticker}: {e}")
        return {
            "ticker": ticker, "agent": "risk_manager",
            "risk_rating": "HIGH", "confidence": 0, "error": str(e),
            "var_metrics": var_metrics,
        }


def _parse_response(raw: str, ticker: str, var_metrics: dict) -> dict:
    result = {
        "ticker": ticker,
        "agent": "risk_manager",
        "risk_rating": "MEDIUM",
        "max_position_size": "2%",
        "key_risks": [],
        "stop_loss_level": None,
        "confidence": 50,
        "summary": "",
        "var_metrics": var_metrics,
        "raw": raw,
    }
    for line in raw.strip().split("\n"):
        if line.startswith("RISK_RATING:"):
            r = line.split(":", 1)[1].strip().upper()
            if r in ["LOW", "MEDIUM", "HIGH", "VERY_HIGH"]:
                result["risk_rating"] = r
        elif line.startswith("MAX_POSITION_SIZE:"):
            result["max_position_size"] = line.split(":", 1)[1].strip()
        elif line.startswith("KEY_RISKS:"):
            result["key_risks"] = [s.strip() for s in line.split(":", 1)[1].split("|")]
        elif line.startswith("STOP_LOSS_LEVEL:"):
            result["stop_loss_level"] = line.split(":", 1)[1].strip()
        elif line.startswith("CONFIDENCE:"):
            try:
                result["confidence"] = int(line.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif line.startswith("SUMMARY:"):
            result["summary"] = line.split(":", 1)[1].strip()
    return result
