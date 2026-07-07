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
RAW_PROFILE = "data/raw2/profile"
RAW_COMP = "data/raw2/comp"
OUT = "data/funds2.json"
BETA_MIN_ABS = 0.05

# Portfolio-Zusammensetzung (morningstar-data-tool X-Ray-Datenpunkte) -> kurze Keys
COMP_SECTORS = {"AA03K": "ba", "AA03L": "co", "AA03M": "cy", "AA03N": "df",
                "AA03O": "he", "AA03P": "in", "AA03Q": "re", "AA03R": "te",
                "AA03S": "en", "AA03T": "fi", "AA03U": "ut"}
COMP_REGIONS = {"HS009": "am", "HS03D": "eu", "HS03C": "as", "HS02N": "em"}
COMP_COUNTRIES = {"HS09L": "us", "HS10Y": "uk", "HS09S": "jp", "HS10G": "de",
                  "HS10F": "fr", "HS10W": "ch", "HS10M": "nl", "HS09O": "cn"}

DATAPOINTS = {
    "RR010": ("sharpe", "1y"), "RR011": ("sharpe", "3y"), "RR012": ("sharpe", "5y"), "RR013": ("sharpe", "10y"),
    "RR122": ("sortino", "1y"), "RR123": ("sortino", "3y"), "RR124": ("sortino", "5y"), "RR125": ("sortino", "10y"),
    "RR147": ("information", "3y"), "RR148": ("information", "5y"), "RR149": ("information", "10y"), "ZS71V": ("information", "1y"),
    "RR002": ("alpha", "1y"), "RR003": ("alpha", "3y"), "RR004": ("alpha", "5y"), "RR005": ("alpha", "10y"),
    "PM004": ("performance", "1m"), "PM006": ("performance", "3m"), "PM008": ("performance", "6m"),
    "PM00C": ("performance", "1y"), "PM00E": ("performance", "3y"), "PM00G": ("performance", "5y"),
    "PM00I": ("performance", "10y"), "PM00M": ("performance", "incep"),
    "RR141": ("trackingerror", "3y"), "RR142": ("trackingerror", "5y"), "RR143": ("trackingerror", "10y"),
}
RISK_DATAPOINTS = {
    "RR014": ("stddev", "1y"), "RR015": ("stddev", "3y"), "RR016": ("stddev", "5y"), "RR017": ("stddev", "10y"),
    "RR00K": ("beta", "1y"), "RR00L": ("beta", "3y"), "RR00M": ("beta", "5y"), "RR00N": ("beta", "10y"),
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


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def profile_fields(p: dict) -> dict:
    """Baut die Profil-/Stammdaten je Fonds aus den Morningstar-Datenpunkten."""
    out = {}
    bench = p.get("OF00L") or p.get("OS38B")          # Prospekt-Benchmark, sonst Kategorie-Index
    if bench and bench not in ("N/A", "NA"):
        out["bench"] = bench
    if p.get("OS38B"):
        out["benchcat"] = p["OS38B"]                  # Morningstar-Kategorie-Index
    if p.get("HR002") and p["HR002"] not in ("NA", "N/A"):
        out["rating"] = p["HR002"]                    # 1..5 Sterne
    if p.get("MMR01") and p["MMR01"] not in ("NA", "N/A", "Not Ratable"):
        out["medalist"] = p["MMR01"]                  # Gold/Silver/Bronze/Neutral/Negative
    ter = _num(p.get("RC0A4"))
    if ter is None:
        ter = _num(p.get("OS00M"))
    if ter is not None:
        out["ter"] = round(ter, 2)                    # laufende Kosten % p.a.
    aum = _num(p.get("OS99B"))
    if aum is not None:
        out["aum"] = aum                              # Fondsvolumen USD
    if p.get("LS468"):
        out["ccy"] = p["LS468"]
    if p.get("OS00F"):
        out["incepdate"] = p["OS00F"]
    y = _num(p.get("PM032"))
    if y is not None:
        out["yield"] = round(y, 2)                    # 12M-Ausschuettungsrendite %
    return out


def comp_fields(c: dict) -> dict | None:
    """Baut die Portfolio-Zusammensetzung (Morningstar X-Ray) je Fonds:
    Anlagemix, Style-Box (Aktien + Renten), Sektoren, Regionen, Länder,
    durchschn. Bonität, Duration, Titelzahl, Top-10-Konzentration."""
    if not c:
        return None

    def num(k):
        try:
            return float(c[k])
        except (KeyError, TypeError, ValueError):
            return None

    out = {}
    eq, bd, ca = num("HS02E"), num("HS02D"), num("HS00X")
    if eq is not None:
        out["eq"] = round(eq, 1)
    if bd is not None:
        out["bd"] = round(bd, 1)
    if ca is not None:
        out["ca"] = round(ca, 1)
    eqp, bdp = eq or 0, bd or 0
    kind = "equity" if (eqp >= bdp and eqp >= 40) else \
           "bond" if (bdp > eqp and bdp >= 40) else "other"
    out["kind"] = kind

    # Aktien-spezifisch
    if c.get("HS05A"):
        out["sEq"] = c["HS05A"]
    mc = num("HS03W")
    if mc is not None and mc > 0:
        out["mc"] = round(mc)
    sec = {d: round(v, 1) for s, d in COMP_SECTORS.items()
           if (v := num(s)) is not None and v != 0}
    if sec:
        out["sec"] = sec
    reg = {d: round(v, 1) for s, d in COMP_REGIONS.items()
           if (v := num(s)) is not None and v != 0}
    if reg:
        out["reg"] = reg
    ctr = {d: round(v, 1) for s, d in COMP_COUNTRIES.items()
           if (v := num(s)) is not None and v != 0}
    if ctr:
        out["ctr"] = ctr

    # Renten-spezifisch (nur wenn nennenswerter Anleiheanteil, sonst Störwerte)
    if bdp >= 25:
        if c.get("HS00L"):
            out["sFi"] = c["HS00L"]
        if c.get("HS00C"):
            out["cr"] = c["HS00C"]
        du = num("HS02F")
        if du is not None:
            out["du"] = round(du, 2)
        nb = num("HS00J")
        if nb is not None and nb > 0:
            out["nb"] = int(nb)

    nh = num("HS008")
    if nh is not None and nh > 0:
        out["nh"] = int(nh)
    t10 = num("HS07J")
    if t10 is not None:
        out["t10"] = round(t10, 1)
    return out


def main() -> None:
    uni = json.load(open(RAW_UNI, encoding="utf-8"))["investments"]
    raw = {}
    for path in sorted(glob.glob(os.path.join(RAW_METRICS, "*.json"))):
        for fid, dps in json.load(open(path, encoding="utf-8")).items():
            raw.setdefault(fid, {}).update(dps)
    prof = {}
    for path in sorted(glob.glob(os.path.join(RAW_PROFILE, "*.json"))):
        for fid, dps in json.load(open(path, encoding="utf-8")).items():
            prof.setdefault(fid, {}).update(dps)
    comp = {}
    for path in sorted(glob.glob(os.path.join(RAW_COMP, "*.json"))):
        for fid, dps in json.load(open(path, encoding="utf-8")).items():
            comp.setdefault(fid, {}).update(dps)

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
        for p in ("1y", "3y", "5y", "10y"):
            if risk.get(f"stddev_{p}") is not None:
                metrics[f"volatility_{p}"] = risk[f"stddev_{p}"]
            if risk.get(f"beta_{p}") is not None:
                metrics[f"beta_{p}"] = risk[f"beta_{p}"]
            s, sd, be = metrics.get(f"sharpe_{p}"), risk.get(f"stddev_{p}"), risk.get(f"beta_{p}")
            if s is not None and sd is not None and be is not None and abs(be) >= BETA_MIN_ABS:
                metrics[f"treynor_{p}"] = round(s * sd / be, 4)
        fund = {
            "id": fid, "isin": meta.get("isin"), "name": meta.get("name", ""),
            "branding": prov, "wkntype": meta.get("type"),
            "category": category, "metrics": metrics,
        }
        fund.update(profile_fields(prof.get(fid, {})))
        cf = comp_fields(comp.get(fid, {}))
        if cf:
            fund["comp"] = cf
        funds.append(fund)

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
