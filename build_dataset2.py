#!/usr/bin/env python3
"""Baut den Datensatz fuer die ZWEITE App (Fonds & ETFs) aus den Rohdaten in
data/raw2/ und schreibt data/funds2.json. Voellig unabhaengig von App 1.

Quellen:
  data/raw2/universe.json     {investments:{id:{isin,name,type}}, not_found:[...]}
                              type: FO=Fonds, FE=ETF
  data/raw2/metrics/*.json    kompakt {id:{datapointId:value}}  (FC001, OF003 +
                              alle Kennzahlen-Datenpunkte), erzeugt aus den
                              morningstar-data-tool Antworten via parse_tool_result2.py

Anbieter-Bucket (provider):
  - type FE                         -> "ETF"
  - Name enthaelt Quoniam / QFS     -> "Quoniam"   (Quoniam wird bei Morningstar
                                       unter Branding "Union Investment" gefuehrt!)
  - Branding Union / Name "Uni..."  -> "Union Investment"
  - sonst                           -> "Sonstige Fonds"
"""
from __future__ import annotations
import glob, json, os
from datetime import date

RAW_UNI = "data/raw2/universe.json"
RAW_METRICS = "data/raw2/metrics"
OUT = "data/funds2.json"
BETA_MIN_ABS = 0.05

DATAPOINTS = {
    "RR010": ("sharpe", "1y"), "RR011": ("sharpe", "3y"), "RR012": ("sharpe", "5y"),
    "RR122": ("sortino", "1y"), "RR123": ("sortino", "3y"), "RR124": ("sortino", "5y"),
    "RR147": ("information", "3y"), "RR148": ("information", "5y"), "ZS71V": ("information", "1y"),
    "RR002": ("alpha", "1y"), "RR003": ("alpha", "3y"), "RR004": ("alpha", "5y"),
    "PM004": ("performance", "1m"), "PM006": ("performance", "3m"), "PM008": ("performance", "6m"),
    "PM00C": ("performance", "1y"), "PM00E": ("performance", "3y"), "PM00G": ("performance", "5y"),
    "RR141": ("trackingerror", "3y"), "RR142": ("trackingerror", "5y"),
}
RISK_DATAPOINTS = {
    "RR014": ("stddev", "1y"), "RR015": ("stddev", "3y"), "RR016": ("stddev", "5y"),
    "RR00K": ("beta", "1y"), "RR00L": ("beta", "3y"), "RR00M": ("beta", "5y"),
}


def _f(v):
    try:
        return round(float(v), 4)
    except (TypeError, ValueError):
        return None


def provider_bucket(name: str, typ: str, branding: str) -> str:
    n = (name or "").lower()
    b = (branding or "").lower()
    if typ == "FE":
        return "ETF"
    if "quoniam" in n or n.startswith("qfs") or "qfs sicav" in n:
        return "Quoniam"
    if "union" in b or n.startswith("uni") or "commodities-invest" in n:
        return "Union Investment"
    return "Sonstige Fonds"


def main() -> None:
    uni = json.load(open(RAW_UNI, encoding="utf-8"))["investments"]
    raw = {}
    for path in sorted(glob.glob(os.path.join(RAW_METRICS, "*.json"))):
        for fid, dps in json.load(open(path, encoding="utf-8")).items():
            raw.setdefault(fid, {}).update(dps)

    funds = []
    for fid, meta in uni.items():
        dps = raw.get(fid, {})
        branding = dps.get("FC001", "")
        category = dps.get("OF003") or "Unbekannt"
        prov = provider_bucket(meta.get("name", ""), meta.get("type", "FO"), branding)
        metrics, risk = {}, {}
        for dp, val in dps.items():
            if dp in DATAPOINTS:
                m, p = DATAPOINTS[dp]
                fv = _f(val)
                if fv is not None:
                    metrics[f"{m}_{p}"] = fv
            elif dp in RISK_DATAPOINTS:
                m, p = RISK_DATAPOINTS[dp]
                fv = _f(val)
                if fv is not None:
                    risk[f"{m}_{p}"] = fv
        # Volatilitaet & Beta direkt; Treynor = Sharpe x StdAbw / Beta
        for p in ("1y", "3y", "5y"):
            if risk.get(f"stddev_{p}") is not None:
                metrics[f"volatility_{p}"] = risk[f"stddev_{p}"]
            if risk.get(f"beta_{p}") is not None:
                metrics[f"beta_{p}"] = risk[f"beta_{p}"]
            s, sd, be = metrics.get(f"sharpe_{p}"), risk.get(f"stddev_{p}"), risk.get(f"beta_{p}")
            if s is not None and sd is not None and be is not None and abs(be) >= BETA_MIN_ABS:
                metrics[f"treynor_{p}"] = round(s * sd / be, 4)
        funds.append({
            "id": fid, "isin": meta.get("isin"), "name": meta.get("name", ""),
            "branding": prov, "wkntype": meta.get("type"),
            "category": category, "metrics": metrics,
        })

    funds.sort(key=lambda f: (f["branding"], f["name"]))
    payload = {
        "meta": {
            "as_of": date.today().isoformat(),
            "source": "Morningstar MCP connector (id-lookup + data-tool)",
            "providers": sorted({f["branding"] for f in funds}),
            "fund_count": len(funds),
        },
        "funds": funds,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(payload, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    by = {}
    for f in funds:
        by[f["branding"]] = by.get(f["branding"], 0) + 1
    wm = sum(1 for f in funds if f["metrics"])
    print(f"Wertpapiere: {len(funds)} | mit Kennzahl: {wm}")
    print("Anbieter-Buckets:", by)


if __name__ == "__main__":
    main()
