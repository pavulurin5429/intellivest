"""
PDF report generation endpoint.
Produces SFDR Article 8 compliant regulatory reports using ReportLab.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from io import BytesIO
from datetime import datetime
from loguru import logger
from .analysis import _cache, _load_from_db

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _fmt_usd(val) -> str:
    if val is None or val == "N/A":
        return "N/A"
    try:
        return f"${float(val):,.0f}"
    except Exception:
        return str(val)


def _fmt_pct(val) -> str:
    if val is None or val == "N/A":
        return "N/A"
    try:
        return f"{float(val):.1%}"
    except Exception:
        return str(val)


def build_pdf(ticker: str, analysis: dict) -> BytesIO:
    """Generate a PDF investment report for a ticker using ReportLab."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title",  parent=styles["Title"],   fontSize=18, textColor=colors.HexColor("#1a1a2e"))
    h2_style    = ParagraphStyle("H2",     parent=styles["Heading2"],fontSize=13, textColor=colors.HexColor("#16213e"))
    body_style  = styles["BodyText"]
    footer_style = ParagraphStyle("Footer", parent=body_style, fontSize=7, textColor=colors.grey)

    elements = []

    # ── Header ────────────────────────────────────────────────────────────────
    elements.append(Paragraph(f"Investment Intelligence Report: {ticker}", title_style))
    elements.append(Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", body_style))
    elements.append(Paragraph("SFDR Article 8 | ESG-Aligned | Regulatory Disclosure", body_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1a1a2e")))
    elements.append(Spacer(1, 0.4 * cm))

    # ── Executive Summary ─────────────────────────────────────────────────────
    fm = (analysis.get("agent_outputs") or {}).get("fund_manager") or {}
    elements.append(Paragraph("Executive Summary", h2_style))
    summary_data = [
        ["Decision",               fm.get("decision",       "N/A")],
        ["Conviction",             fm.get("conviction",     "N/A")],
        ["Target Portfolio Weight",fm.get("target_weight",  "N/A")],
        ["90-Day Price Target",    fm.get("price_target_90d","N/A")],
        ["Credit Score",           f"{analysis.get('credit_score', 'N/A')}/100"],
        ["Market Regime",          analysis.get("regime",   "N/A")],
    ]
    tbl = Table(summary_data, colWidths=[6 * cm, 10 * cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (0, -1), colors.HexColor("#f0f4ff")),
        ("FONTNAME",      (0, 0), (0, -1), "Helvetica-Bold"),
        ("GRID",          (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS",(1, 0), (-1, -1), [colors.white, colors.HexColor("#f9f9f9")]),
    ]))
    elements.append(tbl)
    elements.append(Spacer(1, 0.4 * cm))

    # ── Investment Thesis ─────────────────────────────────────────────────────
    thesis = (
        fm.get("key_thesis")
        or analysis.get("key_thesis")
        or "No thesis available."
    )
    elements.append(Paragraph("Investment Thesis", h2_style))
    elements.append(Paragraph(thesis, body_style))
    elements.append(Spacer(1, 0.3 * cm))

    # ── Agent Debate Summary ──────────────────────────────────────────────────
    elements.append(Paragraph("Multi-Agent Analysis Summary", h2_style))
    agent_data = [["Agent", "Thesis", "Confidence", "Summary"]]
    for key, label in [
        ("fundamentals", "Fundamentals"),
        ("technicals",   "Technicals"),
        ("sentiment",    "Sentiment"),
        ("risk_manager", "Risk Manager"),
    ]:
        agent = (analysis.get("agent_outputs") or {}).get(key) or {}
        t = agent.get("thesis") or agent.get("risk_rating", "N/A")
        c = f"{agent.get('confidence', 'N/A')}%"
        s = (agent.get("summary", "") or "")[:80] + ("..." if len(agent.get("summary", "") or "") > 80 else "")
        agent_data.append([label, t, c, s])

    agent_tbl = Table(agent_data, colWidths=[3.5 * cm, 3 * cm, 2.5 * cm, 8 * cm])
    agent_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID",          (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, colors.HexColor("#f9f9f9")]),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(agent_tbl)
    elements.append(Spacer(1, 0.4 * cm))

    # ── Risk Metrics ──────────────────────────────────────────────────────────
    risk = (analysis.get("agent_outputs") or {}).get("risk_manager") or {}
    var_metrics = risk.get("var_metrics") or {}
    elements.append(Paragraph("Risk Metrics (SFDR Article 8 Disclosure)", h2_style))
    risk_data = [
        ["Metric",                     "Value"],
        ["Risk Rating",                risk.get("risk_rating", "N/A")],
        ["VaR (95%, 1-day)",           _fmt_usd(var_metrics.get("historical_var_95"))],
        ["CVaR / Expected Shortfall",  _fmt_usd(var_metrics.get("cvar_95"))],
        ["Max Historical Drawdown",    _fmt_pct(var_metrics.get("max_drawdown"))],
        ["Annual Volatility",          _fmt_pct(var_metrics.get("annual_vol"))],
        ["Max Recommended Position",   risk.get("max_position_size", "N/A")],
    ]
    risk_tbl = Table(risk_data, colWidths=[8 * cm, 9 * cm])
    risk_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#c0392b")),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID",          (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, colors.HexColor("#f9f9f9")]),
    ]))
    elements.append(risk_tbl)

    # ── Footer ────────────────────────────────────────────────────────────────
    elements.append(Spacer(1, 1 * cm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    elements.append(Paragraph(
        "This report is generated by an AI-powered multi-agent investment intelligence platform. "
        "It does not constitute financial advice. For SFDR Article 8 compliance purposes only. "
        "Past performance does not guarantee future results.",
        footer_style,
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer


@router.get("/{ticker}/pdf")
async def download_report(ticker: str):
    """Download PDF investment report for a ticker."""
    ticker = ticker.upper()

    # 1. Check in-memory cache first
    analysis = _cache.get(ticker)

    # 2. Fall back to Supabase if not in memory
    if not analysis or analysis.get("status") != "complete":
        analysis = _load_from_db(ticker)

    if not analysis or analysis.get("status") != "complete":
        raise HTTPException(
            status_code=404,
            detail=f"No completed analysis for {ticker}. Run POST /api/analyze/{ticker} first.",
        )

    try:
        pdf_buffer = build_pdf(ticker, analysis)
        filename = f"{ticker}_investment_report_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        logger.error(f"PDF generation error for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
