# tools/finance_api.py
"""
Tool per l'estrazione di dati finanziari da Yahoo Finance.
Progettato per essere chiamato da un agent AI che compone
il report mattutino del giornale personale.

Dipendenze:
    pip install yfinance pandas numpy requests

Utilizzo:
    from investment_tool import get_asset_report
    report = get_asset_report("AAPL", pmc=150.0, benchmark="QQQ")
"""

import yfinance as yf
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from config import I_MIEI_INVESTIMENTI

# ─────────────────────────────────────────────
# CONFIGURAZIONE
# ─────────────────────────────────────────────

# Benchmark di default per settore
SECTOR_BENCHMARKS: dict[str, str] = {
    "Technology":       "QQQ",
    "Financial":        "XLF",
    "Energy":           "XLE",
    "Healthcare":       "XLV",
    "Consumer":         "XLY",
    "Industrial":       "XLI",
    "Real Estate":      "IYR",
    "Utilities":        "XLU",
    "Communication":    "XLC",
    "Materials":        "XLB",
    "Default":          "SPY",
}


# ─────────────────────────────────────────────
# FUNZIONI HELPER
# ─────────────────────────────────────────────

def _compute_rsi(prices: pd.Series, period: int = 14) -> float:
    """Calcola RSI (Relative Strength Index) su una serie di prezzi."""
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return round(float(rsi.iloc[-1]), 2)


def _rsi_label(rsi: float) -> str:
    """Interpreta il valore RSI in linguaggio naturale."""
    if rsi >= 80:
        return "Fortemente ipercomprato 🔴"
    elif rsi >= 70:
        return "Ipercomprato ⚠️"
    elif rsi <= 20:
        return "Fortemente ipervenduto 🟢"
    elif rsi <= 30:
        return "Ipervenduto 💚"
    else:
        return "Neutro ⚪"


def _position_in_range(current: float, low: float, high: float) -> dict:
    """
    Calcola la posizione del prezzo corrente nel range 30gg.
    Ritorna percentuale (0% = minimo, 100% = massimo) e label.
    """
    if high == low:
        pct = 50.0
    else:
        pct = round((current - low) / (high - low) * 100, 1)

    if pct >= 85:
        zone = "Vicino ai massimi 🔺"
    elif pct >= 60:
        zone = "Zona alta"
    elif pct >= 40:
        zone = "Zona mediana"
    elif pct >= 15:
        zone = "Zona bassa"
    else:
        zone = "Vicino ai minimi 🔻"

    return {
        "percentuale_nel_range": pct,
        "zona": zone,
        "range_30d_low": round(low, 4),
        "range_30d_high": round(high, 4),
    }


def _get_news(ticker: str, max_items: int = 3) -> list[dict]:
    """
    Recupera le ultime notizie dal feed di Yahoo Finance.
    Ritorna lista di dict con title, publisher, url, published_at.
    """
    try:
        t = yf.Ticker(ticker)
        raw_news = t.news or []
        result = []
        for item in raw_news[:max_items]:
            content = item.get("content", {})
            result.append({
                "titolo":       content.get("title", "N/A"),
                "fonte":        content.get("provider", {}).get("displayName", "N/A"),
                "url":          content.get("canonicalUrl", {}).get("url", "N/A"),
                "pubblicato":   content.get("pubDate", "N/A"),
            })
        return result
    except Exception as e:
        return [{"errore": str(e)}]


def _get_benchmark_ticker(ticker_info: dict) -> str:
    """Sceglie il benchmark appropriato in base al settore dell'asset."""
    sector = ticker_info.get("sector", "Default")
    for key, bench in SECTOR_BENCHMARKS.items():
        if key.lower() in sector.lower():
            return bench
    return SECTOR_BENCHMARKS["Default"]


def _pct_change_period(history: pd.DataFrame, days: int) -> Optional[float]:
    """Calcola la variazione percentuale sugli ultimi N giorni disponibili."""
    if len(history) < 2:
        return None
    subset = history["Close"].dropna()
    if len(subset) < 2:
        return None
    start = subset.iloc[max(0, len(subset) - days - 1)]
    end = subset.iloc[-1]
    return round((end - start) / start * 100, 2)


# ─────────────────────────────────────────────
# FUNZIONE PRINCIPALE
# ─────────────────────────────────────────────

def get_asset_report(
    ticker: str,
    pmc: Optional[float] = None,
    benchmark: Optional[str] = None,
    rsi_period: int = 14,
    range_days: int = 30,
    news_count: int = 3,
) -> dict:
    """
    Estrae un report completo per un singolo asset.

    Args:
        ticker:      Simbolo Yahoo Finance (es. "AAPL", "BTC-USD", "SPY")
        pmc:         Prezzo Medio di Carico personale (opzionale)
        benchmark:   Ticker del benchmark da confrontare (se None, auto-detect)
        rsi_period:  Periodo RSI (default 14)
        range_days:  Giorni per il calcolo del range (default 30)
        news_count:  Numero di notizie da recuperare (default 3)

    Returns:
        dict strutturato con tutti i dati per il report dell'agent.
    """

    ticker = ticker.strip().upper()
    t = yf.Ticker(ticker)

    # ── Metadati ──────────────────────────────
    try:
        info = t.info or {}
    except Exception:
        info = {}

    readable_name = info.get(ticker) or info.get("longName") or info.get("shortName") or ticker
    currency = info.get("currency", "USD")
    asset_type = info.get("quoteType", "N/A")
    sector = info.get("sector", "N/A")
    industry = info.get("industry", "N/A")

    # ── Storia prezzi ─────────────────────────
    history_full = t.history(period="3mo", auto_adjust=True)

    if history_full.empty:
        return {
            "ticker": ticker,
            "nome": readable_name,
            "errore": "Nessun dato storico disponibile da Yahoo Finance.",
        }

    closes = history_full["Close"].dropna()

    # Prezzo corrente / ultima chiusura
    current_price = round(float(closes.iloc[-1]), 4)

    # ── Delta Daily ───────────────────────────
    if len(closes) >= 2:
        prev_close = float(closes.iloc[-2])
        daily_change_pct = round((current_price - prev_close) / prev_close * 100, 2)
        daily_change_abs = round(current_price - prev_close, 4)
    else:
        prev_close = None
        daily_change_pct = None
        daily_change_abs = None

    # ── Delta Storico vs PMC ──────────────────
    if pmc and pmc > 0:
        delta_pmc_pct = round((current_price - pmc) / pmc * 100, 2)
        delta_pmc_abs = round(current_price - pmc, 4)
        in_profit = delta_pmc_pct >= 0
    else:
        delta_pmc_pct = None
        delta_pmc_abs = None
        in_profit = None

    # ── Range 30 giorni ───────────────────────
    history_30 = history_full.tail(range_days)
    range_low = float(history_30["Low"].min())
    range_high = float(history_30["High"].max())
    range_info = _position_in_range(current_price, range_low, range_high)

    # ── RSI ───────────────────────────────────
    if len(closes) >= rsi_period + 1:
        rsi_value = _compute_rsi(closes, rsi_period)
        rsi_status = _rsi_label(rsi_value)
    else:
        rsi_value = None
        rsi_status = "Dati insufficienti"

    # ── Performance aggiuntive ────────────────
    perf_7d  = _pct_change_period(history_full, 7)
    perf_30d = _pct_change_period(history_full, 30)

    # ── Benchmark ─────────────────────────────
    bench_ticker = benchmark or _get_benchmark_ticker(info)

    try:
        bench_hist = yf.Ticker(bench_ticker).history(period="5d", auto_adjust=True)
        bench_closes = bench_hist["Close"].dropna()

        if len(bench_closes) >= 2:
            bench_current = float(bench_closes.iloc[-1])
            bench_prev    = float(bench_closes.iloc[-2])
            bench_daily   = round((bench_current - bench_prev) / bench_prev * 100, 2)
            relative_perf = round(daily_change_pct - bench_daily, 2) if daily_change_pct is not None else None
            outperform    = relative_perf > 0 if relative_perf is not None else None
        else:
            bench_daily = bench_current = relative_perf = outperform = None

    except Exception as e:
        bench_daily = bench_current = relative_perf = outperform = None

    # ── Notizie ───────────────────────────────
    news = _get_news(ticker, news_count)

    # ── Composizione report ───────────────────
    report = {
        # Metadati
        "generato_il":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ticker":        ticker,
        "nome":          readable_name,
        "tipo_asset":    asset_type,
        "settore":       sector,
        "industria":     industry,
        "valuta":        currency,

        # Snapshot prezzo
        "prezzo_attuale": current_price,
        "chiusura_precedente": round(prev_close, 4) if prev_close else None,

        # Delta daily
        "delta_daily": {
            "variazione_pct":  daily_change_pct,
            "variazione_abs":  daily_change_abs,
            "direzione":       "▲ Rialzo" if (daily_change_pct or 0) > 0 else ("▼ Ribasso" if (daily_change_pct or 0) < 0 else "─ Invariato"),
        },

        # Delta vs PMC
        "delta_pmc": {
            "pmc_inserito":    pmc,
            "variazione_pct":  delta_pmc_pct,
            "variazione_abs":  delta_pmc_abs,
            "in_profitto":     in_profit,
            "stato":           ("✅ In profitto" if in_profit else "🔴 In perdita") if in_profit is not None else "N/A (PMC non fornito)",
        },

        # Performance storiche
        "performance": {
            "7_giorni_pct":  perf_7d,
            "30_giorni_pct": perf_30d,
        },

        # Posizione nel range
        "range_30_giorni": range_info,

        # RSI
        "rsi": {
            "valore":  rsi_value,
            "periodo": rsi_period,
            "stato":   rsi_status,
        },

        # Benchmark
        "benchmark": {
            "ticker":                bench_ticker,
            "variazione_daily_pct":  bench_daily,
            "performance_relativa":  relative_perf,
            "outperformance":        outperform,
            "sintesi":               (
                f"{'▲' if outperform else '▼'} {ticker} ha {'sovraperformato' if outperform else 'sottoperformato'} "
                f"{bench_ticker} di {abs(relative_perf):.2f}% oggi"
            ) if relative_perf is not None else "N/A",
        },

        # Notizie
        "notizie_recenti": news,
    }

    return report


# ─────────────────────────────────────────────
# BATCH: più asset in una sola chiamata
# ─────────────────────────────────────────────

def get_portfolio_report() -> list[dict]:
   
    reports = []
    for asset in I_MIEI_INVESTIMENTI:
        ticker = asset["ticker"]
        nome = asset.get("nome", ticker)
        pmc = asset.get("pmc")
        
       # Chiama la funzione di analisi per il singolo ticker
        report = get_asset_report(ticker=ticker, pmc=pmc)
        
        # Sovrascriviamo il nome con quello 'volgare' del config
        report["nome"] = nome 
        reports.append(report)
    return reports

