#!/usr/bin/env python3
"""Baut aus den rohen Morningstar-Antworten (data/raw/) den bereinigten
Datensatz data/funds.json, den das CLI-Tool fund_metrics.py liest.

Die Rohdaten werden bewusst *verbatim* gespeichert (genau die JSON-Antworten
des Morningstar-Konnektors) und hier programmatisch geparst, damit keine
Abschreibfehler entstehen.

Quellen
-------
data/raw/screener/*.json   Screener-Antworten (Fonds-Universum: id, name, kategorie)
                           Branding (Union Investment / Quoniam) wird aus dem
                           Dateinamen abgeleitet: screener_union_*.json bzw.
                           screener_quoniam_*.json
data/raw/metrics/*.json    Antworten des morningstar-data-tool mit den Kennzahlen
                           je Fonds (datapointId -> value)
"""
from __future__ import annotations

import glob
import json
import os
from datetime import date

RAW_SCREENER = "data/raw/screener"
RAW_METRICS = "data/raw/metrics"
RAW_RISK = "data/raw/risk"
OUT = "data/funds.json"

# Beta-Werte nahe null machen die Treynor Ratio (Division durch Beta)
# instabil/unbedeutend; in diesem Fall wird kein Treynor-Wert berechnet.
BETA_MIN_ABS = 0.05

# Datenpunkt-IDs der direkt von Morningstar gelieferten Kennzahlen.
# (Treynor & Calmar werden vom Konnektor nicht bereitgestellt und sind daher
#  nicht enthalten.)
DATAPOINTS = {
    "RR010": ("sharpe", "1y"),
    "RR011": ("sharpe", "3y"),
    "RR012": ("sharpe", "5y"),
    "RR122": ("sortino", "1y"),
    "RR123": ("sortino", "3y"),
    "RR124": ("sortino", "5y"),
    "RR147": ("information", "3y"),
    "RR148": ("information", "5y"),
    "RR002": ("alpha", "1y"),
    "RR003": ("alpha", "3y"),
    "RR004": ("alpha", "5y"),
    # Information Ratio 1 Jahr: eigener Morningstar-Datenpunkt (Active Process
    # Pillar, gross-of-fee). Methodisch leicht abweichend von RR147/RR148
    # (Israelson-adjustiert), aber für die 1-Jahres-Sicht die passende Größe.
    "ZS71V": ("information", "1y"),
    # Performance / absolute Rendite (Total Return Mo-End). 1/3/6 Monate sowie
    # 1/3/5 Jahre (3/5J annualisiert).
    "PM004": ("performance", "1m"),
    "PM006": ("performance", "3m"),
    "PM008": ("performance", "6m"),
    "PM00C": ("performance", "1y"),
    "PM00E": ("performance", "3y"),
    "PM00G": ("performance", "5y"),
    # Tracking Error (Volatilität der Aktivrenditen vs. Benchmark), 3/5 Jahre.
    "RR141": ("trackingerror", "3y"),
    "RR142": ("trackingerror", "5y"),
}

# Hilfsdatenpunkte (Standardabweichung & Beta), aus denen die Treynor Ratio
# berechnet wird:  Treynor = Sharpe x Standardabweichung / Beta
# (gilt exakt, da Morningstars Sharpe und Beta dieselbe Excess-Return-Basis
#  über dem risikofreien Zins verwenden).
RISK_DATAPOINTS = {
    "RR014": ("stddev", "1y"),
    "RR015": ("stddev", "3y"),
    "RR016": ("stddev", "5y"),
    "RR00K": ("beta", "1y"),
    "RR00L": ("beta", "3y"),
    "RR00M": ("beta", "5y"),
}


def _branding_from_filename(path: str) -> str:
    name = os.path.basename(path).lower()
    if "quoniam" in name:
        return "Quoniam"
    if "union" in name:
        return "Union Investment"
    return "Unbekannt"


def load_universe() -> dict[str, dict]:
    """Liest alle Screener-Dateien und liefert id -> {name, category, branding}."""
    funds: dict[str, dict] = {}
    files = sorted(glob.glob(os.path.join(RAW_SCREENER, "*.json")))
    if not files:
        raise SystemExit(f"Keine Screener-Dateien in {RAW_SCREENER} gefunden.")
    for path in files:
        file_branding = _branding_from_filename(path)
        with open(path, encoding="utf-8") as fh:
            payload = json.load(fh)

        # Kompaktformat: {"branding": "...", "funds": [["id","name","category"], ...]}
        if isinstance(payload, dict) and isinstance(payload.get("funds"), list):
            branding = payload.get("branding") or file_branding
            for row in payload["funds"]:
                if not row or not row[0]:
                    continue
                fid, name, category = (list(row) + ["", "", ""])[:3]
                funds.setdefault(
                    fid,
                    {
                        "id": fid,
                        "name": (name or "").strip(),
                        "category": (category or "Unbekannt").strip(),
                        "branding": branding,
                        "metrics": {},
                    },
                )
            continue

        # Rich-Format (verbatim Screener-Antwort)
        for row in payload.get("results", []):
            fid = row.get("morningstar_id")
            if not fid:
                continue
            kd = row.get("key_datapoints", {}) or {}
            category = kd.get("Morningstar Category") or "Unbekannt"
            # Erststreffer gewinnt; spätere (z.B. Dubletten) überschreiben nicht.
            funds.setdefault(
                fid,
                {
                    "id": fid,
                    "name": (row.get("name") or "").strip(),
                    "category": category.strip(),
                    "branding": file_branding,
                    "metrics": {},
                },
            )
    return funds


def _to_float(value) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None


def _store_pair(store: dict[str, float], dp: str, raw_value) -> None:
    mapping = DATAPOINTS.get(dp)
    if not mapping:
        return
    metric, period = mapping
    val = _to_float(raw_value)
    if val is not None:
        store[f"{metric}_{period}"] = val


def load_metrics() -> dict[str, dict[str, float]]:
    """Liest alle Metrik-Dateien und liefert id -> {'sharpe_3y': wert, ...}.

    Es werden zwei Dateiformate unterstützt:

    1. Rich-Format (verbatim die Antwort des morningstar-data-tool):
       {"result": {"F0..": {"values": [{"datapointId": "RR010", "value": "1.29"}, ...]}}}

    2. Kompaktformat (platzsparend):
       {"F0..": {"RR010": "1.29", "RR011": 0.9, ...}, ...}
    """
    by_fund: dict[str, dict[str, float]] = {}
    files = sorted(glob.glob(os.path.join(RAW_METRICS, "*.json")))
    for path in files:
        with open(path, encoding="utf-8") as fh:
            payload = json.load(fh)

        if isinstance(payload, dict) and "result" in payload:
            # Rich-Format
            for fid, body in (payload.get("result") or {}).items():
                store = by_fund.setdefault(fid, {})
                for item in body.get("values", []) or []:
                    _store_pair(store, item.get("datapointId"), item.get("value"))
        elif isinstance(payload, dict):
            # Kompaktformat: Top-Level-Keys sind Fonds-IDs
            for fid, dps in payload.items():
                if not isinstance(dps, dict):
                    continue
                store = by_fund.setdefault(fid, {})
                for dp, raw_value in dps.items():
                    _store_pair(store, dp, raw_value)
    return by_fund


def load_risk() -> dict[str, dict[str, float]]:
    """Liest die Risiko-Hilfsdaten (Standardabweichung & Beta) je Fonds.

    Unterstützt dieselben zwei Dateiformate wie load_metrics() (Rich/Kompakt).
    Liefert id -> {'stddev_3y': .., 'beta_3y': .., ...}.
    """
    by_fund: dict[str, dict[str, float]] = {}
    files = sorted(glob.glob(os.path.join(RAW_RISK, "*.json")))
    for path in files:
        with open(path, encoding="utf-8") as fh:
            payload = json.load(fh)
        if isinstance(payload, dict) and "result" in payload:
            for fid, body in (payload.get("result") or {}).items():
                store = by_fund.setdefault(fid, {})
                for item in body.get("values", []) or []:
                    dp = item.get("datapointId")
                    if dp in RISK_DATAPOINTS:
                        name, period = RISK_DATAPOINTS[dp]
                        val = _to_float(item.get("value"))
                        if val is not None:
                            store[f"{name}_{period}"] = val
        elif isinstance(payload, dict):
            for fid, dps in payload.items():
                if not isinstance(dps, dict):
                    continue
                store = by_fund.setdefault(fid, {})
                for dp, raw_value in dps.items():
                    if dp in RISK_DATAPOINTS:
                        name, period = RISK_DATAPOINTS[dp]
                        val = _to_float(raw_value)
                        if val is not None:
                            store[f"{name}_{period}"] = val
    return by_fund


def compute_treynor(metrics: dict[str, float], risk: dict[str, float]) -> dict[str, float]:
    """Ergänzt treynor_{1y,3y,5y} aus Sharpe, Standardabweichung und Beta."""
    out: dict[str, float] = {}
    for period in ("1y", "3y", "5y"):
        sharpe = metrics.get(f"sharpe_{period}")
        stddev = risk.get(f"stddev_{period}")
        beta = risk.get(f"beta_{period}")
        if sharpe is None or stddev is None or beta is None:
            continue
        if abs(beta) < BETA_MIN_ABS:
            continue
        out[f"treynor_{period}"] = round(sharpe * stddev / beta, 4)
    return out


def main() -> None:
    universe = load_universe()
    metrics = load_metrics()
    risk = load_risk()

    # Alle Fonds-IDs, für die Metrik- ODER Risiko-Daten vorliegen.
    all_ids = set(metrics) | set(risk)
    matched = 0
    for fid in all_ids:
        if fid not in universe:
            continue  # sollte nicht vorkommen
        vals = dict(metrics.get(fid, {}))
        r = risk.get(fid, {})
        # Treynor aus Sharpe/StdAbw/Beta berechnen.
        vals.update(compute_treynor(vals, r))
        # Volatilität (= Standardabweichung) und Beta direkt als Kennzahlen
        # aus den Risiko-Daten übernehmen (kein separater Abruf nötig).
        for period in ("1y", "3y", "5y"):
            if r.get(f"stddev_{period}") is not None:
                vals[f"volatility_{period}"] = r[f"stddev_{period}"]
            if r.get(f"beta_{period}") is not None:
                vals[f"beta_{period}"] = r[f"beta_{period}"]
        if vals:
            universe[fid]["metrics"] = vals
            matched += 1

    funds = sorted(universe.values(), key=lambda f: (f["branding"], f["name"]))
    payload = {
        "meta": {
            "as_of": date.today().isoformat(),
            "source": "Morningstar MCP connector (morningstar-data-tool / screener-tool)",
            "providers": sorted({f["branding"] for f in funds}),
            "fund_count": len(funds),
            "metrics_available": {
                "performance": ["1m", "3m", "6m", "1y", "3y", "5y"],
                "sharpe": ["1y", "3y", "5y"],
                "sortino": ["1y", "3y", "5y"],
                "information": ["1y", "3y", "5y"],
                "alpha": ["1y", "3y", "5y"],
                "treynor": ["1y", "3y", "5y"],
                "volatility": ["1y", "3y", "5y"],
                "beta": ["1y", "3y", "5y"],
                "trackingerror": ["3y", "5y"],
            },
            "treynor_note": (
                "Treynor wird berechnet als Sharpe x Standardabweichung / Beta; "
                "kein Wert, wenn Beta fehlt oder |Beta| < "
                f"{BETA_MIN_ABS}."
            ),
        },
        "funds": funds,
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)

    with_metrics = sum(1 for f in funds if f["metrics"])
    print(f"Universum:           {len(funds)} Fonds")
    print(f"Mit Metrik-Datei:    {matched} Fonds gematcht")
    print(f"Mit >=1 Kennzahl:    {with_metrics} Fonds")
    print(f"Geschrieben:         {OUT}")


if __name__ == "__main__":
    main()
