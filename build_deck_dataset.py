#!/usr/bin/env python3
"""Baut den Snapshot-Datensatz fuer die DRITTE App (Fonds-Analyse-PowerPoint)
aus den Rohdaten in data/raw3/ und schreibt data/funds3.json.

Quellen:
  data/raw3/universe.json     {investments:{fid:{isin,name,type}}, not_found:[...]}
  data/raw3/metrics/*.json    kompakt {fid:{datapointId:value}} (aus
                              morningstar-data-tool via parse_tool_result3.py)
  data/raw3/portfolio/<fid>.json  (optional) normalisierte X-Ray-Daten je Fonds
  data/raw3/holdings/<fid>.json   (optional) Top-Holdings je Fonds

Aufruf:  python3 build_deck_dataset.py [STICHTAG_YYYY-MM-DD]
Ohne Stichtag wird das heutige Datum eingetragen (nur fuer die Anzeige).
"""
from __future__ import annotations
import glob, json, os, sys
from datetime import date

RAW_UNI = "data/raw3/universe.json"
RAW_METRICS = "data/raw3/metrics"
RAW_PORT = "data/raw3/portfolio"
RAW_HOLD = "data/raw3/holdings"
OUT = "data/funds3.json"

# datapointId -> (kennzahl, laufzeit)
RET = {
    "PM004": ("performance", "1m"), "PM006": ("performance", "3m"),
    "PM008": ("performance", "6m"), "PM00C": ("performance", "1y"),
    "PM00E": ("performance", "3y"), "PM00G": ("performance", "5y"),
    "PM00I": ("performance", "10y"), "PM00M": ("performance", "incep"),
}
RATIOS = {
    "RR010": ("sharpe", "1y"), "RR011": ("sharpe", "3y"), "RR012": ("sharpe", "5y"), "RR013": ("sharpe", "10y"),
    "RR122": ("sortino", "1y"), "RR123": ("sortino", "3y"), "RR124": ("sortino", "5y"), "RR125": ("sortino", "10y"),
    "ZS71V": ("information", "1y"), "RR147": ("information", "3y"), "RR148": ("information", "5y"), "RR149": ("information", "10y"),
    "RR002": ("alpha", "1y"), "RR003": ("alpha", "3y"), "RR004": ("alpha", "5y"), "RR005": ("alpha", "10y"),
    "RR00K": ("beta", "1y"), "RR00L": ("beta", "3y"), "RR00M": ("beta", "5y"), "RR00N": ("beta", "10y"),
    "RR014": ("volatility", "1y"), "RR015": ("volatility", "3y"), "RR016": ("volatility", "5y"), "RR017": ("volatility", "10y"),
    "RR141": ("trackingerror", "3y"), "RR142": ("trackingerror", "5y"), "RR143": ("trackingerror", "10y"),
}
# Einzelne Snapshot-Felder
STAR, MEDAL, RISKR = "RR01Y", "MMR01", "RR04W"
NAME, CAT, BRAND, INCEP, SIZE, COST, YIELD = "OS01W", "OF003", "FC001", "OS00F", "OF99A", "OS05P", "PM032"

ALL_DATAPOINTS = (["OS01W", "OF003", "FC001", "OS00F", "OF99A", "OS05P", "PM032",
                   "RR01Y", "MMR01", "RR04W"] + list(RET) + list(RATIOS))


def _f(v):
    try:
        return round(float(v), 4)
    except (TypeError, ValueError):
        return None


def asset_class(category: str, name: str) -> str:
    """Grobe Anlageklasse aus Morningstar-Kategorie (Fallback: Fondsname)."""
    c = (category or "").lower()
    n = (name or "").lower()
    t = c + " " + n
    if any(k in t for k in ("commodit", "rohstoff", "gold", "precious metal", "silver")):
        return "Rohstoffe & Gold"
    if "convertible" in t or "wandel" in t:
        return "Wandelanleihen"
    if any(k in t for k in ("property", "real estate", "immobil")):
        return "Immobilien"
    if any(k in t for k in ("money market", "geldmarkt", "reserve", "liquid", "ultrashort", "ultra short")):
        return "Geldmarkt & Liquidität"
    if any(k in t for k in ("bond", "fixed income", "renten", "credit", "corporate", "government",
                            "high yield", "covered", "renta", "treasury", "sovereign", "debt",
                            "structured credit", "aggregate")):
        return "Renten"
    if any(k in t for k in ("equity", "aktien", "stock", "dividend", "dax", "stoxx", "msci",
                            "small cap", "large-cap", "mid-cap", "hightech", "biopharma",
                            "blockchain", "industrie", "infrastruktur", "sector")):
        return "Aktien"
    if any(k in t for k in ("allocation", "mischfonds", "multi-asset", "multi asset", "balanced",
                            "flexible", "aspirant", "aggressive", "moderate", "cautious")):
        return "Mischfonds / Multi-Asset"
    return "Sonstige"


# Reihenfolge der Anlageklassen in der Praesentation
CLASS_ORDER = ["Aktien", "Renten", "Wandelanleihen", "Rohstoffe & Gold",
               "Immobilien", "Geldmarkt & Liquidität", "Mischfonds / Multi-Asset", "Sonstige"]


def main():
    stichtag = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    uni = json.load(open(RAW_UNI, encoding="utf-8"))
    inv = uni["investments"]
    not_found = uni.get("not_found", [])

    raw = {}
    for path in sorted(glob.glob(os.path.join(RAW_METRICS, "*.json"))):
        for fid, dps in json.load(open(path, encoding="utf-8")).items():
            raw.setdefault(fid, {}).update(dps)

    funds = []
    for fid, meta in inv.items():
        dps = raw.get(fid, {})
        name = dps.get(NAME) or meta.get("name", "")
        category = dps.get(CAT) or "—"
        klass = asset_class(category, name)
        metrics = {}
        for dp, val in dps.items():
            if dp in RET:
                k, p = RET[dp]
            elif dp in RATIOS:
                k, p = RATIOS[dp]
            else:
                continue
            fv = _f(val)
            if fv is not None:
                metrics[f"{k}_{p}"] = fv
        fund = {
            "id": fid,
            "isin": meta.get("isin"),
            "name": name,
            "type": meta.get("type"),
            "branding": dps.get(BRAND) or "",
            "category": category,
            "asset_class": klass,
            "inception": dps.get(INCEP),
            "fund_size_usd": _f(dps.get(SIZE)),
            "cost": _f(dps.get(COST)),
            "yield": _f(dps.get(YIELD)),
            "star_rating": dps.get(STAR),
            "medalist": dps.get(MEDAL),
            "risk_rating": dps.get(RISKR),
            "metrics": metrics,
        }
        # optionale X-Ray / Holdings
        pf = os.path.join(RAW_PORT, f"{fid}.json")
        hd = os.path.join(RAW_HOLD, f"{fid}.json")
        if os.path.exists(pf):
            fund["portfolio"] = json.load(open(pf, encoding="utf-8"))
        if os.path.exists(hd):
            fund["holdings"] = json.load(open(hd, encoding="utf-8"))
        funds.append(fund)

    funds.sort(key=lambda f: (CLASS_ORDER.index(f["asset_class"]) if f["asset_class"] in CLASS_ORDER else 99,
                              f["category"], f["name"]))

    by_class = {}
    for f in funds:
        by_class[f["asset_class"]] = by_class.get(f["asset_class"], 0) + 1

    payload = {
        "meta": {
            "stichtag": stichtag,
            "generated": date.today().isoformat(),
            "source": "Morningstar MCP connector (id-lookup + data-tool + portfolio-analysis)",
            "fund_count": len(funds),
            "not_found": not_found,
            "by_class": by_class,
            "class_order": CLASS_ORDER,
        },
        "funds": funds,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(payload, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    wm = sum(1 for f in funds if f["metrics"])
    print(f"Stichtag {stichtag} | Fonds: {len(funds)} | mit Kennzahlen: {wm} | nicht gefunden: {len(not_found)}")
    print("Anlageklassen:", json.dumps(by_class, ensure_ascii=False))


if __name__ == "__main__":
    main()
