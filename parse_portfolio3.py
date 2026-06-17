#!/usr/bin/env python3
"""Normalisiert Morningstar-X-Ray-/Holdings-Antworten in das vom Deck-Builder
erwartete kompakte Portfolio-Format und legt je Fonds eine Datei unter
data/raw3/portfolio/<fid>.json (Asset-Allokation + Sektoren) sowie
data/raw3/holdings/<fid>.json (Top-Positionen) ab.

Eingabe: EINE JSON-Datei, die der Skill aus den (kleinen, inline gelieferten)
X-Ray-Antworten zusammenstellt, im Schema:

    { "<fid>": {
        "asset_allocation": <rohe xray_response der asset_allocation-Analyse>,
        "equity_sectors":   <rohe xray_response der equity_sectors-Analyse>,
        "fixed_income_sectors": <... optional ...>,
        "holdings": <rohe Antwort des morningstar-fund-holdings-tool ODER
                     portfolio-analysis top_holdings> },
      ... weitere Fonds ... }

Aufruf:  python3 parse_portfolio3.py <eingabe.json>
"""
from __future__ import annotations
import json, os, sys

PORT_DIR = "data/raw3/portfolio"
HOLD_DIR = "data/raw3/holdings"

SECTOR_DE = {
    "basic_materials": "Grundstoffe", "communication_services": "Kommunikation",
    "consumer_cyclical": "Zykl. Konsum", "consumer_defensive": "Defens. Konsum",
    "energy": "Energie", "financial_services": "Finanzen", "healthcare": "Gesundheit",
    "industrials": "Industrie", "real_estate": "Immobilien", "technology": "Technologie",
    "utilities": "Versorger",
}
# Super-Sektoren (Aggregate) NICHT als Einzel-Sektor ausweisen
SUPER = {"cyclical", "defensive", "sensitive", "not_classified", "portfolio_analyzed"}

FI_SECTOR_DE = {
    "government": "Staatsanleihen", "corporate": "Unternehmensanl.", "securitized": "Verbrieft",
    "municipal": "Kommunal", "cash_and_equivalents": "Cash", "derivative": "Derivate",
}


def _xray(raw):
    if not isinstance(raw, dict):
        return {}
    return (raw.get("xray_response", {}) or {}).get("analysis", {}) or raw.get("analysis", {}) or {}


def norm_asset_alloc(raw):
    a = _xray(raw).get("asset_allocation", {})
    p = a.get("portfolio", {})
    if not p:
        return None
    def net(k):
        v = p.get(k, {})
        return v.get("net") if isinstance(v, dict) else v
    eq = (net("us_equity") or 0) + (net("non_us_equity") or 0)
    return {
        "equity": round(eq, 2),
        "bonds": round(net("bonds") or 0, 2),
        "cash": round(net("cash") or 0, 2),
        "other": round((net("other") or 0) + (net("not_classified") or 0), 2),
    }


def norm_sectors(raw):
    a = _xray(raw).get("equity_sectors", {})
    p = a.get("portfolio", {})
    out = {}
    for k, v in p.items():
        if k in SUPER or not isinstance(v, (int, float)):
            continue
        if k in SECTOR_DE and v:
            out[SECTOR_DE[k]] = round(v, 2)
    return out or None


def norm_fi_sectors(raw):
    a = _xray(raw).get("fixed_income_sectors", {})
    p = a.get("portfolio", {})
    out = {}
    for k, v in p.items():
        if isinstance(v, (int, float)) and v and k in FI_SECTOR_DE:
            out[FI_SECTOR_DE[k]] = round(v, 2)
    return out or None


def norm_holdings(raw):
    """Akzeptiert fund-holdings-tool oder portfolio-analysis top_holdings."""
    if not isinstance(raw, dict):
        return None
    # portfolio-analysis top_holdings
    a = _xray(raw).get("top_holdings")
    cand = None
    if isinstance(a, dict):
        cand = a.get("holdings") or a.get("portfolio")
    if cand is None and "results" in raw and isinstance(raw["results"], list):
        # morningstar-fund-holdings-tool: {results:[{holdings:{<fid>:[...]}}]}
        for entry in raw["results"]:
            hd = entry.get("holdings") if isinstance(entry, dict) else None
            if isinstance(hd, dict):
                for v in hd.values():
                    if isinstance(v, list):
                        cand = v; break
            if cand:
                break
    if cand is None:
        # weitere Varianten: {result:{<fid>:{holdings:[...]}}} oder {holdings:[...]}
        if isinstance(raw.get("holdings"), list):
            cand = raw["holdings"]
        elif "result" in raw and isinstance(raw["result"], dict):
            for v in raw["result"].values():
                if isinstance(v, dict) and isinstance(v.get("holdings"), list):
                    cand = v["holdings"]; break
    if not isinstance(cand, list):
        return None
    out = []
    for h in cand:
        if not isinstance(h, dict):
            continue
        name = h.get("name") or h.get("security_name") or h.get("holding_name") or ""
        w = next((h.get(k) for k in ("weight", "holding_weight", "percent_net_assets")
                  if h.get(k) is not None), None)
        try:
            w = round(float(w), 2)
        except (TypeError, ValueError):
            w = None
        if name:
            out.append({"name": name, "weight": w})
    return out or None


def main(src):
    data = json.load(open(src, encoding="utf-8"))
    os.makedirs(PORT_DIR, exist_ok=True); os.makedirs(HOLD_DIR, exist_ok=True)
    np = nh = 0
    for fid, blocks in data.items():
        pf = {}
        aa = norm_asset_alloc(blocks.get("asset_allocation", {}))
        if aa:
            pf["asset_allocation"] = aa
        sec = norm_sectors(blocks.get("equity_sectors", {}))
        if sec:
            pf["sectors"] = sec
        fis = norm_fi_sectors(blocks.get("fixed_income_sectors", {}))
        if fis:
            pf["fi_sectors"] = fis
        if pf:
            json.dump(pf, open(os.path.join(PORT_DIR, f"{fid}.json"), "w", encoding="utf-8"),
                      ensure_ascii=False)
            np += 1
        hold = norm_holdings(blocks.get("holdings", {}))
        if hold:
            json.dump(hold, open(os.path.join(HOLD_DIR, f"{fid}.json"), "w", encoding="utf-8"),
                      ensure_ascii=False)
            nh += 1
    print(f"Portfolio: {np} Fonds | Holdings: {nh} Fonds")


if __name__ == "__main__":
    main(sys.argv[1])
